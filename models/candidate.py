from typing import Optional
from pydantic import BaseModel, Field

class CandidateEvidence(BaseModel):
    evidence_id: str
    category: str
    topic: str
    evidence_text: str
    source_section: str = ""
    source_page: Optional[int] = None
    confidence: float = Field(.5, ge=0, le=1)

class CandidateProfile(BaseModel):
    candidate_name: str = ""
    email: str = ""
    phone: str = ""
    summary: str = ""
    total_experience_years: Optional[float] = None
    evidence: list[CandidateEvidence] = Field(default_factory=list)
