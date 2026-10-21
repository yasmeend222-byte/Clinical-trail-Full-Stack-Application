import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from ..auth import audit, get_current_researcher
from ..database import get_db
from ..models import Patient, PatientTrialMatch, Researcher
from ..schemas import PatientIn, match_out, patient_out
from ..services.fhir import parse_fhir, to_fhir_bundle
from ..services.matcher import run_patient_matching, sort_matches

router = APIRouter(prefix="/api/patients", tags=["patients"], dependencies=[Depends(get_current_researcher)])


def _get_patient(db: Session, patient_id: int) -> Patient:
    p = db.get(Patient, patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    return p


@router.get("")
def list_patients(q: str = "", gender: str = "", limit: int = 200, offset: int = 0, db: Session = Depends(get_db)):
    stmt = select(Patient)
    if q:
        like = f"%{q}%"
        # diagnoses/medications are JSON - search their text representation too
        stmt = stmt.where(or_(Patient.name.ilike(like), Patient.mrn.ilike(like),
                              Patient.clinical_notes.ilike(like), Patient.medical_history.ilike(like),
                              func.lower(cast(Patient.diagnoses, String)).like(f"%{q.lower()}%")))
    if gender:
        stmt = stmt.where(Patient.gender == gender)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Patient.name).limit(min(limit, 1000)).offset(offset))
    return {"total": total, "items": [patient_out(p) for p in rows]}


def _save_patient(db: Session, data: dict, source: str, patient: Patient | None = None) -> Patient:
    if patient is None:
        if db.scalar(select(Patient).where(Patient.mrn == data["mrn"])):
            raise HTTPException(409, f"A patient with MRN {data['mrn']} already exists")
        patient = Patient(source=source)
        db.add(patient)
    for k, v in data.items():
        setattr(patient, k, v)
    return patient


@router.post("", status_code=201)
def create_patient(body: PatientIn, db: Session = Depends(get_db), r: Researcher = Depends(get_current_researcher)):
    p = _save_patient(db, body.model_dump(), "manual")
    db.flush()
    audit(db, r, "patient.create", p.mrn)
    db.commit()
    return patient_out(p, detail=True)


@router.post("/import/fhir")
async def import_fhir(file: UploadFile = File(...), db: Session = Depends(get_db),
                      r: Researcher = Depends(get_current_researcher)):
    try:
        data = json.loads(await file.read())
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid JSON: {exc}") from exc
    created, updated = [], []
    for rec in parse_fhir(data):
        existing = db.scalar(select(Patient).where(Patient.mrn == rec["mrn"]))
        p = _save_patient(db, rec, "fhir", existing)
        (updated if existing else created).append(p)
    db.flush()
    audit(db, r, "patient.import_fhir", f"{len(created)} created, {len(updated)} updated from {file.filename}")
    db.commit()
    return {"created": [patient_out(p) for p in created], "updated": [patient_out(p) for p in updated]}


@router.get("/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    return patient_out(_get_patient(db, patient_id), detail=True)


@router.put("/{patient_id}")
def update_patient(patient_id: int, body: PatientIn, db: Session = Depends(get_db),
                   r: Researcher = Depends(get_current_researcher)):
    p = _get_patient(db, patient_id)
    clash = db.scalar(select(Patient).where(Patient.mrn == body.mrn, Patient.id != p.id))
    if clash:
        raise HTTPException(409, f"A patient with MRN {body.mrn} already exists")
    _save_patient(db, body.model_dump(), p.source, p)
    audit(db, r, "patient.update", p.mrn)
    db.commit()
    return patient_out(p, detail=True)


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: int, db: Session = Depends(get_db), r: Researcher = Depends(get_current_researcher)):
    p = _get_patient(db, patient_id)
    audit(db, r, "patient.delete", p.mrn)
    db.delete(p)
    db.commit()


@router.get("/{patient_id}/fhir")
def export_fhir(patient_id: int, db: Session = Depends(get_db)):
    return to_fhir_bundle(_get_patient(db, patient_id))


@router.post("/{patient_id}/match")
def match_patient(patient_id: int, db: Session = Depends(get_db), r: Researcher = Depends(get_current_researcher)):
    p = _get_patient(db, patient_id)
    matches = run_patient_matching(db, p)
    audit(db, r, "patient.match", f"{p.mrn}: screened against {len(matches)} trials")
    db.commit()
    return [match_out(m) for m in matches]


@router.get("/{patient_id}/matches")
def patient_matches(patient_id: int, db: Session = Depends(get_db)):
    _get_patient(db, patient_id)
    rows = db.scalars(select(PatientTrialMatch).where(PatientTrialMatch.patient_id == patient_id))
    return [match_out(m) for m in sort_matches(list(rows))]
