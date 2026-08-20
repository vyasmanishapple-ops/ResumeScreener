from models.evidence import RequirementMatch
from models.job import JDRequirement
from services.validation_engine import validate

def test_valid_result():
    r = JDRequirement(
        requirement_id="1",
        category="TECHNICAL_SKILL",
        name="Python",
        description="",
    )
    m = RequirementMatch(
        requirement_id="1",
        requirement_name="Python",
        status="NO_EVIDENCE",
    )
    assert validate(
        [r], [m], {"final_score": 0}
    ) == []
