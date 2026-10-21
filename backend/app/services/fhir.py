"""HL7 FHIR R4 import / export (Patient, Condition, MedicationStatement/Request,
Observation, DocumentReference)."""
import base64
from datetime import date

from fastapi import HTTPException

from ..models import Patient


def _cc_text(cc: dict | None) -> str:
    if not cc:
        return ""
    if cc.get("text"):
        return cc["text"]
    for coding in cc.get("coding", []):
        if coding.get("display"):
            return coding["display"]
    return ""


def _ref_id(ref: str | None) -> str:
    return (ref or "").split("/")[-1].replace("urn:uuid:", "")


def _empty_record() -> dict:
    return {"diagnoses": [], "medications": [], "lab_results": [], "history": [], "notes": []}


def parse_fhir(data: dict) -> list[dict]:
    """Return a list of patient dicts ready to be stored."""
    if not isinstance(data, dict) or "resourceType" not in data:
        raise HTTPException(400, "Not a FHIR resource (missing resourceType)")
    if data["resourceType"] == "Bundle":
        resources = [e.get("resource", {}) for e in data.get("entry", [])]
    else:
        resources = [data]

    patients: dict[str, dict] = {}
    records: dict[str, dict] = {}
    for r in resources:
        if r.get("resourceType") == "Patient":
            pid = r.get("id") or str(len(patients) + 1)
            patients[pid] = r
            records.setdefault(pid, _empty_record())
    if not patients:
        raise HTTPException(400, "No Patient resource found in the FHIR payload")
    only = next(iter(patients)) if len(patients) == 1 else None

    for r in resources:
        rtype = r.get("resourceType")
        if rtype == "Patient":
            continue
        subject = _ref_id((r.get("subject") or r.get("patient") or {}).get("reference")) or only
        if subject not in records:
            continue
        rec = records[subject]
        if rtype == "Condition":
            name = _cc_text(r.get("code"))
            status = ((r.get("clinicalStatus") or {}).get("coding") or [{}])[0].get("code", "active")
            if name and status in ("resolved", "inactive", "remission"):
                rec["history"].append(f"History of {name} ({status}).")
            elif name:
                rec["diagnoses"].append(name)
        elif rtype in ("MedicationStatement", "MedicationRequest"):
            name = _cc_text(r.get("medicationCodeableConcept")) or \
                (r.get("medicationReference") or {}).get("display", "")
            status = r.get("status", "active")
            if name:
                if status in ("stopped", "completed", "cancelled", "entered-in-error"):
                    rec["history"].append(f"Previously treated with {name} ({status}).")
                else:
                    rec["medications"].append(name)
        elif rtype == "Observation":
            name = _cc_text(r.get("code"))
            when = (r.get("effectiveDateTime") or r.get("issued") or "")[:10]
            if "valueQuantity" in r:
                q = r["valueQuantity"]
                rec["lab_results"].append({"name": name, "value": q.get("value"), "unit": q.get("unit", ""),
                                           "date": when})
            elif "valueString" in r:
                rec["notes"].append(f"{name}: {r['valueString']}")
            elif "valueCodeableConcept" in r:
                rec["notes"].append(f"{name}: {_cc_text(r['valueCodeableConcept'])}")
            for comp in r.get("component", []):
                if "valueQuantity" in comp:
                    q = comp["valueQuantity"]
                    rec["lab_results"].append({"name": _cc_text(comp.get("code")), "value": q.get("value"),
                                               "unit": q.get("unit", ""), "date": when})
        elif rtype == "DocumentReference":
            for content in r.get("content", []):
                att = content.get("attachment", {})
                if att.get("data"):
                    try:
                        rec["notes"].append(base64.b64decode(att["data"]).decode("utf-8", errors="replace"))
                    except Exception:
                        pass

    out = []
    for pid, p in patients.items():
        names = p.get("name") or [{}]
        n = names[0]
        full = n.get("text") or " ".join(n.get("given", []) + [n.get("family", "")]).strip() or f"Patient {pid}"
        identifier = (p.get("identifier") or [{}])[0].get("value") or f"FHIR-{pid}"
        birth = None
        if p.get("birthDate"):
            try:
                birth = date.fromisoformat(p["birthDate"][:10])
            except ValueError:
                birth = None
        addr = (p.get("address") or [{}])[0]
        rec = records[pid]
        out.append({
            "mrn": identifier,
            "name": full,
            "birth_date": birth,
            "gender": p.get("gender", "unknown"),
            "demographics": {k: v for k, v in {"city": addr.get("city"), "state": addr.get("state"),
                                                "country": addr.get("country"), "fhir_id": pid}.items() if v},
            "diagnoses": rec["diagnoses"],
            "medications": rec["medications"],
            "lab_results": rec["lab_results"],
            "medical_history": " ".join(rec["history"]),
            "clinical_notes": "\n".join(rec["notes"]),
        })
    return out


def to_fhir_bundle(p: Patient) -> dict:
    pid = f"pt-{p.id}"
    ref = {"reference": f"Patient/{pid}"}
    given, _, family = p.name.rpartition(" ")
    entries = [{"resource": {
        "resourceType": "Patient", "id": pid,
        "identifier": [{"system": "urn:contextsync:mrn", "value": p.mrn}],
        "name": [{"text": p.name, "given": [given or p.name], "family": family if given else ""}],
        "gender": p.gender, "birthDate": p.birth_date.isoformat() if p.birth_date else None,
        "address": [{k: v for k, v in (p.demographics or {}).items() if k in ("city", "state", "country")}],
    }}]
    for i, dx in enumerate(p.diagnoses or []):
        entries.append({"resource": {"resourceType": "Condition", "id": f"{pid}-cond-{i}", "subject": ref,
                                     "clinicalStatus": {"coding": [{"code": "active"}]}, "code": {"text": dx}}})
    for i, med in enumerate(p.medications or []):
        entries.append({"resource": {"resourceType": "MedicationStatement", "id": f"{pid}-med-{i}",
                                     "subject": ref, "status": "active",
                                     "medicationCodeableConcept": {"text": med}}})
    for i, lab in enumerate(p.lab_results or []):
        entries.append({"resource": {"resourceType": "Observation", "id": f"{pid}-obs-{i}", "subject": ref,
                                     "status": "final", "code": {"text": lab.get("name")},
                                     "effectiveDateTime": lab.get("date") or None,
                                     "valueQuantity": {"value": lab.get("value"), "unit": lab.get("unit")}}})
    notes = "\n".join(x for x in (p.medical_history, p.clinical_notes) if x)
    if notes:
        entries.append({"resource": {"resourceType": "DocumentReference", "id": f"{pid}-doc", "subject": ref,
                                     "status": "current", "content": [{"attachment": {
                                         "contentType": "text/plain",
                                         "data": base64.b64encode(notes.encode()).decode()}}]}})
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}
