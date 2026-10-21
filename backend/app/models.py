"""ORM models - mirrors the UML class diagram (Researcher, ClinicalTrial,
EligibilityCriteria, Patient, PatientTrialMatch) plus an audit log."""
from datetime import date, datetime, timezone

from sqlalchemy import (JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Researcher(Base):
    __tablename__ = "researchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(60), default="Clinical Trial Coordinator")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    trials: Mapped[list["ClinicalTrial"]] = relationship(back_populates="researcher")


class ClinicalTrial(Base):
    __tablename__ = "clinical_trials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trial_code: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(300))
    phase: Mapped[str] = mapped_column(String(40), default="")
    condition: Mapped[str] = mapped_column(String(200), default="")
    sponsor: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    protocol_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="recruiting")
    researcher_id: Mapped[int | None] = mapped_column(ForeignKey("researchers.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    researcher: Mapped[Researcher | None] = relationship(back_populates="trials")
    criteria: Mapped[list["EligibilityCriterion"]] = relationship(
        back_populates="trial", cascade="all, delete-orphan", order_by="EligibilityCriterion.position")
    matches: Mapped[list["PatientTrialMatch"]] = relationship(
        back_populates="trial", cascade="all, delete-orphan")


class EligibilityCriterion(Base):
    __tablename__ = "eligibility_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("clinical_trials.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(20))  # inclusion | exclusion
    category: Mapped[str] = mapped_column(String(30))  # demographic | diagnosis | lab | medication | other
    description: Mapped[str] = mapped_column(Text)
    structured_rule: Mapped[dict] = mapped_column(JSON, default=dict)
    required_evidence: Mapped[str] = mapped_column(String(300), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)

    trial: Mapped[ClinicalTrial] = relationship(back_populates="criteria")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mrn: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String(20), default="unknown")
    demographics: Mapped[dict] = mapped_column(JSON, default=dict)
    diagnoses: Mapped[list] = mapped_column(JSON, default=list)
    medications: Mapped[list] = mapped_column(JSON, default=list)
    lab_results: Mapped[list] = mapped_column(JSON, default=list)  # [{name, value, unit, date}]
    medical_history: Mapped[str] = mapped_column(Text, default="")
    clinical_notes: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(30), default="manual")  # manual | fhir | seed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    matches: Mapped[list["PatientTrialMatch"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan")


class PatientTrialMatch(Base):
    __tablename__ = "patient_trial_matches"
    __table_args__ = (UniqueConstraint("trial_id", "patient_id", name="uq_trial_patient"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("clinical_trials.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    eligibility_status: Mapped[str] = mapped_column(String(30))  # eligible | potentially_eligible | ineligible
    confidence_score: Mapped[float] = mapped_column(Float)
    semantic_score: Mapped[float] = mapped_column(Float, default=0.0)
    criteria_results: Mapped[list] = mapped_column(JSON, default=list)
    matched_criteria: Mapped[list] = mapped_column(JSON, default=list)
    unmet_criteria: Mapped[list] = mapped_column(JSON, default=list)
    unknown_criteria: Mapped[list] = mapped_column(JSON, default=list)
    missing_tests: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text, default="")
    explanation_source: Mapped[str] = mapped_column(String(20), default="template")
    review_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approved | rejected
    review_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    trial: Mapped[ClinicalTrial] = relationship(back_populates="matches")
    patient: Mapped[Patient] = relationship(back_populates="matches")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    researcher_id: Mapped[int | None] = mapped_column(ForeignKey("researchers.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
