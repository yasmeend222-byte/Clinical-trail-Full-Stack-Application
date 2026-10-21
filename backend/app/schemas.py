"""Request models and response serializers."""
from datetime import date

from pydantic import BaseModel, Field

from .models import ClinicalTrial, EligibilityCriterion, Patient, PatientTrialMatch, Researcher
from .services.matcher import compute_age


# ---------- requests ----------
class LoginIn(BaseModel):
    email: str
    password: str


class RegisterIn(BaseModel):
    name: str = Field(min_length=2)
    email: str = Field(min_length=5)
    password: str = Field(min_length=6)
    role: str = "Clinical Trial Coordinator"


class TrialIn(BaseModel):
    title: str = Field(min_length=3)
    trial_code: str = ""
    phase: str = ""
    condition: str = ""
    sponsor: str = ""
    description: str = ""
    protocol_text: str = Field(min_length=10)
    status: str = "recruiting"


class TrialUpdate(BaseModel):
    title: str | None = None
    phase: str | None = None
    condition: str | None = None
    sponsor: str | None = None
    description: str | None = None
    status: str | None = None
    protocol_text: str | None = None


class ExtractIn(BaseModel):
    protocol_text: str


class CriterionIn(BaseModel):
    type: str = Field(pattern="^(inclusion|exclusion)$")
    description: str = Field(min_length=3)


class LabIn(BaseModel):
    name: str
    value: float
    unit: str = ""
    date: str = ""


class PatientIn(BaseModel):
    mrn: str = Field(min_length=1)
    name: str = Field(min_length=1)
    birth_date: date | None = None
    gender: str = "unknown"
    demographics: dict = {}
    diagnoses: list[str] = []
    medications: list[str] = []
    lab_results: list[LabIn] = []
    medical_history: str = ""
    clinical_notes: str = ""


class ReviewIn(BaseModel):
    review_status: str = Field(pattern="^(pending|approved|rejected|contacted|enrolled)$")
    review_notes: str = ""


# ---------- serializers ----------
def researcher_out(r: Researcher) -> dict:
    return {"id": r.id, "name": r.name, "email": r.email, "role": r.role}


def criterion_out(c: EligibilityCriterion) -> dict:
    return {"id": c.id, "type": c.type, "category": c.category, "description": c.description,
            "structured_rule": c.structured_rule, "required_evidence": c.required_evidence,
            "position": c.position}


def trial_out(t: ClinicalTrial, detail: bool = False) -> dict:
    counts = {"eligible": 0, "potentially_eligible": 0, "ineligible": 0}
    for m in t.matches:
        counts[m.eligibility_status] = counts.get(m.eligibility_status, 0) + 1
    out = {
        "id": t.id, "trial_code": t.trial_code, "title": t.title, "phase": t.phase, "condition": t.condition,
        "sponsor": t.sponsor, "description": t.description, "status": t.status,
        "created_at": t.created_at, "last_matched_at": t.last_matched_at,
        "criteria_count": len(t.criteria),
        "inclusion_count": sum(1 for c in t.criteria if c.type == "inclusion"),
        "exclusion_count": sum(1 for c in t.criteria if c.type == "exclusion"),
        "match_counts": counts,
        "created_by": t.researcher.name if t.researcher else None,
    }
    if detail:
        out["protocol_text"] = t.protocol_text
        out["criteria"] = [criterion_out(c) for c in t.criteria]
    return out


def patient_out(p: Patient, detail: bool = False) -> dict:
    out = {
        "id": p.id, "mrn": p.mrn, "name": p.name, "gender": p.gender,
        "birth_date": p.birth_date, "age": compute_age(p.birth_date),
        "diagnoses": p.diagnoses or [], "medications": p.medications or [],
        "source": p.source, "updated_at": p.updated_at,
    }
    if detail:
        out.update(demographics=p.demographics or {}, lab_results=p.lab_results or [],
                   medical_history=p.medical_history, clinical_notes=p.clinical_notes)
    return out


def match_out(m: PatientTrialMatch, detail: bool = False) -> dict:
    out = {
        "id": m.id, "trial_id": m.trial_id, "patient_id": m.patient_id,
        "trial_title": m.trial.title if m.trial else None,
        "trial_code": m.trial.trial_code if m.trial else None,
        "patient": patient_out(m.patient) if m.patient else None,
        "eligibility_status": m.eligibility_status, "confidence_score": m.confidence_score,
        "semantic_score": m.semantic_score,
        "matched_count": len(m.matched_criteria or []), "unmet_count": len(m.unmet_criteria or []),
        "unknown_count": len(m.unknown_criteria or []),
        "missing_tests": m.missing_tests or [],
        "review_status": m.review_status, "updated_at": m.updated_at,
        "explanation_source": m.explanation_source,
    }
    if detail:
        out.update(criteria_results=m.criteria_results, matched_criteria=m.matched_criteria,
                   unmet_criteria=m.unmet_criteria, unknown_criteria=m.unknown_criteria,
                   explanation=m.explanation, review_notes=m.review_notes)
    return out
