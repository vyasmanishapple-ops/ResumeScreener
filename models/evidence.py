from pydantic import BaseModel, Field

VALID_STATUSES = {
    "EXPLICIT_MATCH","PARTIAL_MATCH","RELATED_EVIDENCE",
    "NO_EVIDENCE","CONTRADICTED"
}

class RequirementMatch(BaseModel):
    requirement_id: str
    requirement_name: str
    status: str
    evidence_text: str = ""
    source_section: str = ""
    confidence: float = Field(.5, ge=0, le=1)
    explanation: str = ""
