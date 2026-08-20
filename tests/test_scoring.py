from models.evidence import RequirementMatch
from models.job import JDRequirement
from services.scoring_engine import calculate_score


def test_score_is_bounded():
    r = JDRequirement(
        requirement_id="1", category="TECHNICAL_SKILL", name="Python",
        description="Python", importance_level="HIGH", weight=8,
    )
    m = RequirementMatch(
        requirement_id="1", requirement_name="Python", status="EXPLICIT_MATCH",
    )
    result = calculate_score([r], [m], [])
    assert 0 <= result["final_score"] <= 100


def test_not_required_is_excluded_from_score():
    required = JDRequirement(
        requirement_id="1", category="TECHNICAL_SKILL", name="Python",
        importance_level="HIGH", weight=8,
    )
    optional = JDRequirement(
        requirement_id="2", category="EDUCATION", name="MBA",
        importance_level="NOT_REQUIRED", weight=0, skill_type="NONE",
    )
    matches = [
        RequirementMatch(requirement_id="1", requirement_name="Python", status="EXPLICIT_MATCH"),
        RequirementMatch(requirement_id="2", requirement_name="MBA", status="NO_EVIDENCE"),
    ]
    result = calculate_score([required, optional], matches, [])
    assert result["base_score"] == 100


def test_soft_failure_does_not_fail_gate():
    r = JDRequirement(
        requirement_id="1", category="TECHNICAL_SKILL", name="Agile",
        importance_level="HIGH", weight=8, skill_type="SOFT",
    )
    m = RequirementMatch(
        requirement_id="1", requirement_name="Agile", status="NO_EVIDENCE",
    )
    result = calculate_score([r], [m], [])
    assert result["gate_status"] == "PASSED"


def test_hard_failure_fails_gate():
    r = JDRequirement(
        requirement_id="1", category="EXPERIENCE", name="20 years",
        importance_level="CRITICAL", weight=10, skill_type="HARD",
    )
    m = RequirementMatch(
        requirement_id="1", requirement_name="20 years", status="NO_EVIDENCE",
    )
    result = calculate_score([r], [m], [])
    assert result["gate_status"] == "FAILED"


def test_or_group_uses_best_match():
    react = JDRequirement(
        requirement_id="react", category="TECHNICAL_SKILL", name="React",
        importance_level="HIGH", weight=8,
        relationship_group="frontend_framework", relationship_operator="OR",
    )
    angular = JDRequirement(
        requirement_id="angular", category="TECHNICAL_SKILL", name="Angular",
        importance_level="HIGH", weight=8,
        relationship_group="frontend_framework", relationship_operator="OR",
    )
    matches = [
        RequirementMatch(requirement_id="react", requirement_name="React", status="EXPLICIT_MATCH"),
        RequirementMatch(requirement_id="angular", requirement_name="Angular", status="NO_EVIDENCE"),
    ]
    result = calculate_score([react, angular], matches, [])
    assert result["base_score"] == 100
