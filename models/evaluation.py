from datetime import datetime
from pydantic import BaseModel, Field
from .evidence import RequirementMatch
from .keywords import KeywordDetection

class EvaluationResult(BaseModel):
    evaluation_number: str = ""
    candidate_name: str
    candidate_email: str
    job_title: str
    base_score: float = Field(ge=0, le=100)
    keyword_adjustment: float
    final_score: float = Field(ge=0, le=100)
    gate_status: str
    recommendation: str
    requirement_matches: list[RequirementMatch] = Field(default_factory=list)
    keyword_detections: list[KeywordDetection] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    recruiter_decision: str = ""
    recruiter_notes: str = ""
    model_name: str = ""
    prompt_version: str = ""
    scoring_version: str = ""
    created_at: datetime
