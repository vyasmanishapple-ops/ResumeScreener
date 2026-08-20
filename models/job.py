from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class JDCategory(str, Enum):
    EXPERIENCE = "EXPERIENCE"
    TECHNICAL_SKILL = "TECHNICAL_SKILL"
    FUNCTIONAL_SKILL = "FUNCTIONAL_SKILL"
    QUALIFICATION = "QUALIFICATION"
    RESPONSIBILITY = "RESPONSIBILITY"
    LEADERSHIP = "LEADERSHIP"
    EDUCATION = "EDUCATION"
    CERTIFICATION = "CERTIFICATION"
    BEHAVIORAL = "BEHAVIORAL"
    INDUSTRY = "INDUSTRY"
    WORK_ARRANGEMENT = "WORK_ARRANGEMENT"
    LOCATION = "LOCATION"
    SUCCESS_MEASURE = "SUCCESS_MEASURE"
    OTHER = "OTHER"


class SourceClassification(str, Enum):
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    INFORMATIONAL = "INFORMATIONAL"


class JDRequirement(BaseModel):
    requirement_id: str
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


class JDAnalysis(BaseModel):
    job_title: str = ""
    summary: str = ""
    requirements: list[JDRequirement] = Field(default_factory=list)
    rejected_requirements: list[str] = Field(default_factory=list)
