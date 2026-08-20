from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from database.database import Base

class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    candidate_name: Mapped[str] = mapped_column(String(255), default="")
    candidate_email: Mapped[str] = mapped_column(String(255), index=True)
    job_title: Mapped[str] = mapped_column(String(255), default="")
    base_score: Mapped[float] = mapped_column(Float)
    keyword_adjustment: Mapped[float] = mapped_column(Float)
    final_score: Mapped[float] = mapped_column(Float)
    gate_status: Mapped[str] = mapped_column(String(30))
    recommendation: Mapped[str] = mapped_column(String(100))
    payload_json: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(50))
    scoring_version: Mapped[str] = mapped_column(String(50))
    recruiter_decision: Mapped[str] = mapped_column(String(50), default="")
    recruiter_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class JobDescriptionVersion(Base):
    __tablename__ = "job_description_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_title: Mapped[str] = mapped_column(String(255), default="")
    raw_jd_text: Mapped[str] = mapped_column(Text)
    ai_generated_model_json: Mapped[str] = mapped_column(Text)
    approved_model_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
