from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..auth import audit, get_current_researcher
from ..database import get_db
from ..models import ClinicalTrial, EligibilityCriterion, PatientTrialMatch, Researcher
from ..nlp.criteria_extractor import extract_criteria, structure_criterion
from ..schemas import CriterionIn, ExtractIn, TrialIn, TrialUpdate, criterion_out, match_out, trial_out
from ..services.documents import extract_text
from ..services.matcher import run_trial_matching, sort_matches

router = APIRouter(prefix="/api/trials", tags=["trials"], dependencies=[Depends(get_current_researcher)])


def _get_trial(db: Session, trial_id: int) -> ClinicalTrial:
    t = db.get(ClinicalTrial, trial_id)
    if not t:
        raise HTTPException(404, "Trial not found")
    return t


def _set_criteria(t: ClinicalTrial, protocol_text: str) -> None:
    t.criteria.clear()
    for c in extract_criteria(protocol_text):
        t.criteria.append(EligibilityCriterion(**c))


@router.get("")
def list_trials(q: str = "", status: str = "", db: Session = Depends(get_db)):
    stmt = select(ClinicalTrial).order_by(ClinicalTrial.created_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(ClinicalTrial.title.ilike(like), ClinicalTrial.condition.ilike(like),
                              ClinicalTrial.trial_code.ilike(like)))
    if status:
        stmt = stmt.where(ClinicalTrial.status == status)
    return [trial_out(t) for t in db.scalars(stmt)]


@router.post("/extract-preview")
def extract_preview(body: ExtractIn):
    """Run criteria extraction without saving (lets the researcher review first)."""
    return {"criteria": extract_criteria(body.protocol_text)}


@router.post("/extract-file")
async def extract_file(file: UploadFile = File(...)):
    text = extract_text(file.filename, await file.read())
    if len(text.strip()) < 10:
        raise HTTPException(400, "No readable text found in the document")
    return {"protocol_text": text, "criteria": extract_criteria(text)}


@router.post("", status_code=201)
def create_trial(body: TrialIn, db: Session = Depends(get_db), r: Researcher = Depends(get_current_researcher)):
    t = ClinicalTrial(**body.model_dump(), researcher_id=r.id)
    _set_criteria(t, body.protocol_text)
    if not t.criteria:
        raise HTTPException(422, "No eligibility criteria could be extracted from the protocol text")
    db.add(t)
    db.flush()
    if not t.trial_code:
        t.trial_code = f"CS-{t.id:04d}"
    audit(db, r, "trial.create", f"{t.trial_code}: {t.title}")
    db.commit()
    return trial_out(t, detail=True)


@router.get("/{trial_id}")
def get_trial(trial_id: int, db: Session = Depends(get_db)):
    return trial_out(_get_trial(db, trial_id), detail=True)


@router.put("/{trial_id}")
def update_trial(trial_id: int, body: TrialUpdate, db: Session = Depends(get_db),
                 r: Researcher = Depends(get_current_researcher)):
    t = _get_trial(db, trial_id)
    data = body.model_dump(exclude_none=True)
    reextract = "protocol_text" in data and data["protocol_text"] != t.protocol_text
    for k, v in data.items():
        setattr(t, k, v)
    if reextract:
        _set_criteria(t, t.protocol_text)
    audit(db, r, "trial.update", t.trial_code)
    db.commit()
    return trial_out(t, detail=True)


@router.delete("/{trial_id}", status_code=204)
def delete_trial(trial_id: int, db: Session = Depends(get_db), r: Researcher = Depends(get_current_researcher)):
    t = _get_trial(db, trial_id)
    audit(db, r, "trial.delete", f"{t.trial_code}: {t.title}")
    db.delete(t)
    db.commit()


@router.post("/{trial_id}/criteria", status_code=201)
def add_criterion(trial_id: int, body: CriterionIn, db: Session = Depends(get_db)):
    t = _get_trial(db, trial_id)
    c = EligibilityCriterion(**structure_criterion(body.description, body.type),
                             position=max((x.position for x in t.criteria), default=-1) + 1)
    t.criteria.append(c)
    db.commit()
    return criterion_out(c)


@router.put("/{trial_id}/criteria/{criterion_id}")
def update_criterion(trial_id: int, criterion_id: int, body: CriterionIn, db: Session = Depends(get_db)):
    c = db.get(EligibilityCriterion, criterion_id)
    if not c or c.trial_id != trial_id:
        raise HTTPException(404, "Criterion not found")
    for k, v in structure_criterion(body.description, body.type).items():
        setattr(c, k, v)
    db.commit()
    return criterion_out(c)


@router.delete("/{trial_id}/criteria/{criterion_id}", status_code=204)
def delete_criterion(trial_id: int, criterion_id: int, db: Session = Depends(get_db)):
    c = db.get(EligibilityCriterion, criterion_id)
    if not c or c.trial_id != trial_id:
        raise HTTPException(404, "Criterion not found")
    db.delete(c)
    db.commit()


@router.post("/{trial_id}/match")
def match_trial(trial_id: int, db: Session = Depends(get_db), r: Researcher = Depends(get_current_researcher)):
    t = _get_trial(db, trial_id)
    if not t.criteria:
        raise HTTPException(422, "Trial has no eligibility criteria")
    matches = run_trial_matching(db, t)
    eligible = sum(1 for m in matches if m.eligibility_status == "eligible")
    audit(db, r, "trial.match", f"{t.trial_code}: {len(matches)} patients screened, {eligible} eligible")
    db.commit()
    return [match_out(m) for m in matches]


@router.get("/{trial_id}/matches")
def trial_matches(trial_id: int, status: str = "", db: Session = Depends(get_db)):
    _get_trial(db, trial_id)
    stmt = select(PatientTrialMatch).where(PatientTrialMatch.trial_id == trial_id)
    if status:
        stmt = stmt.where(PatientTrialMatch.eligibility_status == status)
    return [match_out(m) for m in sort_matches(list(db.scalars(stmt)))]
