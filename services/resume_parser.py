from llm.client import LocalLLM
from llm.prompts import RESUME_SYSTEM
from llm.schemas import CandidateSchema
from models.candidate import CandidateProfile

def parse_resume(text, model=None):
    result = LocalLLM(model).structured(
        CandidateSchema, RESUME_SYSTEM, "CANDIDATE RESUME:\n" + text
    )
    return CandidateProfile.model_validate(result.model_dump())
