from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_researcher
from ..config import LLM_MODEL, llm_enabled
from ..database import engine, get_db
from ..models import AuditLog, ClinicalTrial, Patient, PatientTrialMatch, Researcher

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_researcher)])


@router.get("")
def dashboard(db: Session = Depends(get_db)):
    by_status = dict(db.execute(select(PatientTrialMatch.eligibility_status, func.count())
                                .group_by(PatientTrialMatch.eligibility_status)).all())
    by_review = dict(db.execute(select(PatientTrialMatch.review_status, func.count())
                                .group_by(PatientTrialMatch.review_status)).all())
    trials = []
    for t in db.scalars(select(ClinicalTrial).order_by(ClinicalTrial.created_at.desc()).limit(8)):
        counts = {"eligible": 0, "potentially_eligible": 0, "ineligible": 0}
        for m in t.matches:
            counts[m.eligibility_status] += 1
        trials.append({"id": t.id, "trial_code": t.trial_code, "title": t.title, "condition": t.condition,
                       "phase": t.phase, "status": t.status, "match_counts": counts,
                       "last_matched_at": t.last_matched_at})
    logs = db.execute(select(AuditLog, Researcher.name).join(Researcher, AuditLog.researcher_id == Researcher.id,
                                                              isouter=True)
                      .order_by(AuditLog.created_at.desc()).limit(10)).all()
    return {
        "patients": db.scalar(select(func.count()).select_from(Patient)),
        "trials": db.scalar(select(func.count()).select_from(ClinicalTrial)),
        "recruiting_trials": db.scalar(select(func.count()).select_from(ClinicalTrial)
                                       .where(ClinicalTrial.status == "recruiting")),
        "matches": sum(by_status.values()),
        "by_status": {k: by_status.get(k, 0) for k in ("eligible", "potentially_eligible", "ineligible")},
        "by_review": by_review,
        "trials_overview": trials,
        "activity": [{"action": a.action, "detail": a.detail, "at": a.created_at, "by": name} for a, name in logs],
        "system": {"llm_enabled": llm_enabled(), "llm_model": LLM_MODEL if llm_enabled() else None,
                   "database": engine.dialect.name, "embedding": "TF-IDF (word + char n-gram) vector store"},
    }
