"""Hybrid eligibility engine: structured rule evaluation + semantic similarity.

For every (trial, patient) pair each criterion is evaluated to
met / not_met / unknown with evidence, a confidence score is computed,
missing diagnostic tests are identified and an explanation is generated.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import LLM_TOP_K, llm_enabled
from ..models import ClinicalTrial, EligibilityCriterion, Patient, PatientTrialMatch
from ..nlp.concepts import find_mentions, lab_key_for_name, split_sentences
from ..nlp.vocabulary import expand_condition, expand_medication, lab_label
from .explainer import explain
from .vector_store import VectorStore

SEMANTIC_THRESHOLD = 0.30
SOURCE_CONFIDENCE = {"direct": 1.0, "absence": 0.85, "semantic": 0.7}
STATUS_ORDER = {"eligible": 0, "potentially_eligible": 1, "ineligible": 2}


@dataclass
class PatientProfile:
    patient: Patient
    age: int | None
    gender: str
    conditions: dict[str, str] = field(default_factory=dict)
    negated_conditions: dict[str, str] = field(default_factory=dict)
    medications: dict[str, str] = field(default_factory=dict)
    negated_medications: dict[str, str] = field(default_factory=dict)
    labs: dict[str, dict] = field(default_factory=dict)
    sentences: list[str] = field(default_factory=list)


def compute_age(birth: date | None, today: date | None = None) -> int | None:
    if not birth:
        return None
    today = today or date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def patient_document(p: Patient) -> str:
    labs = " ".join(f"{l.get('name', '')}" for l in (p.lab_results or []))
    return " . ".join([
        "Diagnoses: " + ", ".join(p.diagnoses or []),
        "Medications: " + ", ".join(p.medications or []),
        "Labs: " + labs,
        p.medical_history or "",
        p.clinical_notes or "",
    ])


def build_profile(p: Patient) -> PatientProfile:
    prof = PatientProfile(patient=p, age=compute_age(p.birth_date), gender=(p.gender or "unknown").lower())

    def add(target: dict, expand, canonical: str, evidence: str):
        for c in expand(canonical):
            target.setdefault(c, evidence)

    # structured problem / medication lists (treated as affirmed facts)
    for dx in p.diagnoses or []:
        for m in find_mentions(dx, kinds=("condition",)):
            target = prof.negated_conditions if m.negated else prof.conditions
            add(target, expand_condition, m.canonical, f"Diagnosis list: “{dx}”")
        prof.conditions.setdefault(dx.lower().strip(), f"Diagnosis list: “{dx}”")
    for med in p.medications or []:
        for m in find_mentions(med, kinds=("medication",)):
            add(prof.medications, expand_medication, m.canonical, f"Medication list: “{med}”")

    # unstructured history + notes (negation-aware)
    for label, text in (("Medical history", p.medical_history), ("Clinical note", p.clinical_notes)):
        for m in find_mentions(text or "", kinds=("condition", "medication")):
            ev = f"{label}: “{m.sentence}”"
            if m.kind == "condition":
                add(prof.negated_conditions if m.negated else prof.conditions, expand_condition, m.canonical, ev)
            else:
                add(prof.negated_medications if m.negated else prof.medications, expand_medication, m.canonical, ev)

    # labs: most recent value per normalized test
    for lab in p.lab_results or []:
        key = lab_key_for_name(str(lab.get("name", "")))
        try:
            value = float(lab.get("value"))
        except (TypeError, ValueError):
            continue
        if not key:
            continue
        current = prof.labs.get(key)
        if current is None or str(lab.get("date") or "") >= str(current.get("date") or ""):
            prof.labs[key] = {"value": value, "unit": lab.get("unit", ""), "date": lab.get("date", ""),
                              "name": lab.get("name", key)}

    prof.sentences = split_sentences(p.medical_history) + split_sentences(p.clinical_notes) + \
        [f"Diagnosis: {d}" for d in p.diagnoses or []] + [f"Medication: {m}" for m in p.medications or []]
    return prof


def _in_bounds(value: float, check: dict) -> bool:
    if "min" in check:
        if value < check["min"] or (value == check["min"] and not check.get("min_inclusive", True)):
            return False
    if "max" in check:
        if value > check["max"] or (value == check["max"] and not check.get("max_inclusive", True)):
            return False
    return True


def evaluate_check(check: dict, prof: PatientProfile, ctype: str, store: VectorStore) -> dict:
    """Returns {result: True|False|None, evidence, source, missing?}.

    `result` answers "does the patient have the property described by the check?"."""
    kind = check["kind"]
    if kind == "age":
        if prof.age is None:
            return {"result": None, "evidence": "Date of birth not recorded", "source": "missing",
                    "missing": "Date of birth"}
        return {"result": _in_bounds(prof.age, check), "evidence": f"Age {prof.age} years", "source": "direct"}

    if kind == "gender":
        if prof.gender not in ("male", "female"):
            return {"result": None, "evidence": "Sex not recorded", "source": "missing", "missing": "Recorded sex"}
        return {"result": prof.gender == check["value"], "evidence": f"Recorded sex: {prof.gender}",
                "source": "direct"}

    if kind in ("condition", "medication"):
        found = prof.conditions if kind == "condition" else prof.medications
        negated = prof.negated_conditions if kind == "condition" else prof.negated_medications
        for name in check["any_of"]:
            if name in found:
                return {"result": True, "evidence": found[name], "source": "direct"}
        for name in check["any_of"]:
            if name in negated:
                return {"result": False, "evidence": "Explicitly negated — " + negated[name], "source": "direct"}
        what = " / ".join(check["any_of"])
        where = "diagnoses or clinical notes" if kind == "condition" else "medication list or notes"
        return {"result": False, "evidence": f"No record of {what} in {where}", "source": "absence"}

    if kind == "lab":
        lab = prof.labs.get(check["lab"])
        if lab is None:
            return {"result": None, "evidence": f"No {lab_label(check['lab'])} result on file", "source": "missing",
                    "missing": lab_label(check["lab"])}
        date_txt = f" ({lab['date']})" if lab.get("date") else ""
        return {"result": _in_bounds(lab["value"], check),
                "evidence": f"{lab_label(check['lab'])} = {lab['value']:g} {lab.get('unit') or ''}{date_txt}".strip(),
                "source": "direct"}

    # free text -> semantic evidence search in notes
    sentence, score = store.best_sentence(check["text"], prof.sentences)
    if score >= SEMANTIC_THRESHOLD:
        return {"result": True if ctype == "inclusion" else None,
                "evidence": f"Possible evidence (similarity {score:.2f}): “{sentence}”", "source": "semantic",
                "similarity": round(score, 3)}
    if ctype == "inclusion":
        return {"result": None, "evidence": "No supporting evidence found in notes — manual review needed",
                "source": "missing", "similarity": round(score, 3)}
    return {"result": False, "evidence": "No evidence of this exclusion in the record", "source": "absence",
            "similarity": round(score, 3)}


def evaluate_criterion(c: EligibilityCriterion, prof: PatientProfile, store: VectorStore) -> dict:
    checks = (c.structured_rule or {}).get("checks", [])
    results = []
    for chk in checks:
        r = evaluate_check(chk, prof, c.type, store)
        results.append({"label": chk.get("label", chk["kind"]), "kind": chk["kind"], **r})

    values = [r["result"] for r in results]
    if c.type == "inclusion":
        if any(v is False for v in values):
            status, conf = "not_met", 0.0
        elif values and all(v is True for v in values):
            status = "met"
            conf = min(SOURCE_CONFIDENCE.get(r["source"], 1.0) for r in results)
        else:
            status, conf = "unknown", 0.4
    else:  # exclusion: the criterion "applies" when all its checks hold
        falses = [r for r in results if r["result"] is False]
        if falses:
            status = "met"
            conf = max(SOURCE_CONFIDENCE.get(r["source"], 1.0) for r in falses)
        elif values and all(v is True for v in values):
            status, conf = "not_met", 0.0
        else:
            status, conf = "unknown", 0.4

    missing = [r["missing"] for r in results if r.get("missing")] if status == "unknown" else []
    return {
        "criterion_id": c.id, "type": c.type, "category": c.category, "description": c.description,
        "status": status, "confidence": conf, "checks": results, "missing": missing,
    }


def evaluate_patient(criteria: list[EligibilityCriterion], prof: PatientProfile, store: VectorStore,
                     semantic: float) -> dict:
    results = [evaluate_criterion(c, prof, store) for c in criteria]
    statuses = [r["status"] for r in results]
    if "not_met" in statuses:
        status = "ineligible"
    elif all(s == "met" for s in statuses):
        status = "eligible"
    else:
        status = "potentially_eligible"

    rule_score = sum(r["confidence"] for r in results) / len(results) if results else 0.0
    score = 100 * (0.85 * rule_score + 0.15 * semantic)
    if status == "ineligible":
        score *= 0.4

    # missing data only matters if the patient isn't already ruled out
    missing_tests, seen = [], set()
    for r in results if status != "ineligible" else []:
        for m in r["missing"]:
            if m not in seen:
                seen.add(m)
                missing_tests.append({"test": m, "reason": r["description"]})
    return {
        "eligibility_status": status,
        "confidence_score": round(score, 1),
        "semantic_score": round(semantic, 3),
        "criteria_results": results,
        "matched_criteria": [r["description"] for r in results if r["status"] == "met"],
        "unmet_criteria": [r["description"] for r in results if r["status"] == "not_met"],
        "unknown_criteria": [r["description"] for r in results if r["status"] == "unknown"],
        "missing_tests": missing_tests,
    }


def trial_query_text(trial: ClinicalTrial) -> str:
    inc = " . ".join(c.description for c in trial.criteria if c.type == "inclusion")
    return f"{trial.title} . {trial.condition} . {trial.description} . {inc}"


def _upsert(db: Session, trial: ClinicalTrial, patient: Patient, result: dict) -> PatientTrialMatch:
    match = db.scalar(select(PatientTrialMatch).where(PatientTrialMatch.trial_id == trial.id,
                                                      PatientTrialMatch.patient_id == patient.id))
    if match is None:
        match = PatientTrialMatch(trial_id=trial.id, patient_id=patient.id)
        db.add(match)
    for k, v in result.items():
        setattr(match, k, v)
    match.updated_at = datetime.now(timezone.utc)
    return match


def _explain_all(pairs: list[tuple[ClinicalTrial, Patient, PatientProfile, dict]]) -> None:
    """Template explanation for all; LLM explanation for the top-K viable candidates."""
    ranked = sorted(pairs, key=lambda x: (STATUS_ORDER[x[3]["eligibility_status"]], -x[3]["confidence_score"]))
    llm_budget = LLM_TOP_K if llm_enabled() else 0
    for trial, patient, prof, result in ranked:
        use_llm = llm_budget > 0 and result["eligibility_status"] != "ineligible"
        text, source = explain(trial, patient, prof.age, result, use_llm=use_llm)
        if source == "llm":
            llm_budget -= 1
        result["explanation"], result["explanation_source"] = text, source


def _normalize(scores: dict) -> dict:
    top = max(scores.values(), default=0.0)
    return {k: (v / top if top > 0 else 0.0) for k, v in scores.items()}


def run_trial_matching(db: Session, trial: ClinicalTrial) -> list[PatientTrialMatch]:
    """Evaluate every patient against one trial (trial -> ranked candidates)."""
    patients = list(db.scalars(select(Patient)))
    if not patients:
        return []
    store = VectorStore({p.id: patient_document(p) for p in patients},
                        extra_corpus=[c.description for c in trial.criteria])
    semantic = _normalize(store.query(trial_query_text(trial)))
    pairs = []
    for p in patients:
        prof = build_profile(p)
        pairs.append((trial, p, prof, evaluate_patient(trial.criteria, prof, store, semantic.get(p.id, 0.0))))
    _explain_all(pairs)
    matches = [_upsert(db, trial, p, r) for _, p, _, r in pairs]
    trial.last_matched_at = datetime.now(timezone.utc)
    db.commit()
    return sort_matches(matches)


def run_patient_matching(db: Session, patient: Patient) -> list[PatientTrialMatch]:
    """Evaluate one patient against every recruiting trial (personalized trial matching)."""
    trials = list(db.scalars(select(ClinicalTrial).where(ClinicalTrial.status == "recruiting")))
    if not trials:
        return []
    store = VectorStore({t.id: trial_query_text(t) for t in trials}, extra_corpus=[patient_document(patient)])
    semantic = _normalize(store.query(patient_document(patient)))
    prof = build_profile(patient)
    pairs = [(t, patient, prof, evaluate_patient(t.criteria, prof, store, semantic.get(t.id, 0.0)))
             for t in trials]
    _explain_all(pairs)
    matches = [_upsert(db, t, patient, r) for t, _, _, r in pairs]
    db.commit()
    return sort_matches(matches)


def sort_matches(matches: list[PatientTrialMatch]) -> list[PatientTrialMatch]:
    return sorted(matches, key=lambda m: (STATUS_ORDER.get(m.eligibility_status, 3), -m.confidence_score))
