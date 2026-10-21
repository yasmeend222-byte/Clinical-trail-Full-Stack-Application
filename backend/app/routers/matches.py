from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import audit, get_current_researcher
from ..config import llm_enabled
from ..database import get_db
from ..models import PatientTrialMatch, Researcher
from ..schemas import ReviewIn, match_out
from ..services.explainer import explain
from ..services.matcher import compute_age

router = APIRouter(prefix="/api/matches", tags=["matches"], dependencies=[Depends(get_current_researcher)])


def _get_match(db: Session, match_id: int) -> PatientTrialMatch:
    m = db.get(PatientTrialMatch, match_id)
    if not m:
        raise HTTPException(404, "Match not found")
    return m


@router.get("/{match_id}")
def get_match(match_id: int, db: Session = Depends(get_db)):
    return match_out(_get_match(db, match_id), detail=True)


@router.patch("/{match_id}/review")
def review_match(match_id: int, body: ReviewIn, db: Session = Depends(get_db),
                 r: Researcher = Depends(get_current_researcher)):
    m = _get_match(db, match_id)
    m.review_status, m.review_notes = body.review_status, body.review_notes
    audit(db, r, "match.review", f"{m.patient.mrn} / {m.trial.trial_code}: {body.review_status}")
    db.commit()
    return match_out(m, detail=True)


@router.post("/{match_id}/explain")
def regenerate_explanation(match_id: int, db: Session = Depends(get_db)):
    """Regenerate the explanation, using the LLM when one is configured."""
    m = _get_match(db, match_id)
    result = {
        "eligibility_status": m.eligibility_status, "confidence_score": m.confidence_score,
        "criteria_results": m.criteria_results, "missing_tests": m.missing_tests,
    }
    text, source = explain(m.trial, m.patient, compute_age(m.patient.birth_date), result, use_llm=llm_enabled())
    m.explanation, m.explanation_source = text, source
    db.commit()
    return match_out(m, detail=True)
