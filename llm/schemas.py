from typing import Optional
from pydantic import BaseModel, Field
from models.job import JDCategory, SourceClassification


class JDRequirementSchema(BaseModel):
    requirement_id: str = ""
    category: JDCategory = JDCategory.OTHER
    name: str
    description: str = ""

    importance_level: str = "MEDIUM"
    weight: int = Field(5, ge=0, le=10)

    minimum_years: Optional[float] = None
    minimum_threshold: Optional[str] = None

    relationship_group: Optional[str] = None
    relationship_operator: str = "NONE"
    parent_requirement_id: Optional[str] = None

    evidence_expectation: str = ""
    source_text: str = ""
    source_section_heading: str = ""
    source_classification: SourceClassification = SourceClassification.REQUIRED
    skill_type: str = "SOFT"


class JDAnalysisSchema(BaseModel):
    job_title: str = ""
    summary: str = ""
    requirements: list[JDRequirementSchema] = Field(default_factory=list)


class EvidenceSchema(BaseModel):
    evidence_id: str
    category: str
    topic: str
    evidence_text: str
    source_section: str = ""
    source_page: Optional[int] = None
    confidence: float = Field(.5, ge=0, le=1)


class CandidateSchema(BaseModel):
    candidate_name: str = ""
    email: str = ""
    phone: str = ""
    summary: str = ""
    total_experience_years: Optional[float] = None
    evidence: list[EvidenceSchema] = Field(default_factory=list)


class MatchSchema(BaseModel):
    requirement_id: str
    requirement_name: str
    status: str
    evidence_text: str = ""
    source_section: str = ""
    confidence: float = Field(.5, ge=0, le=1)
    explanation: str = ""


class KeywordContext(BaseModel):
    keyword: str
    detected: bool = False
    relevant: bool = False
    context: str = ""


class KeywordAnalysisSchema(BaseModel):
    detections: list[KeywordContext] = Field(default_factory=list)
