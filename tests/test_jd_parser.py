from models.job import JDRequirement
from services.jd_parser import _source_is_supported, normalize_importance


def test_source_text_must_exist_in_jd():
    jd = "Experience with React and AWS."
    assert _source_is_supported(jd, "Experience with React")
    assert not _source_is_supported(jd, "Experience with Kubernetes")


def test_ai_not_required_is_converted_to_low():
    r = JDRequirement(
        requirement_id="1",
        category="TECHNICAL_SKILL",
        name="React",
        importance_level="NOT_REQUIRED",
        weight=0,
    )
    normalize_importance(r)
    assert r.importance_level == "LOW"
    assert r.weight == 3


def test_weight_is_derived_from_importance():
    r = JDRequirement(
        requirement_id="1",
        category="EXPERIENCE",
        name="Experience",
        importance_level="HIGH",
        weight=1,
    )
    normalize_importance(r)
    assert r.weight == 8


def test_simple_or_list_is_split_into_atomic_requirements():
    from services.jd_parser import _repair_or_groups, _generate_ids_and_groups

    r = JDRequirement(
        requirement_id="bad",
        category="TECHNICAL_SKILL",
        name="Strong proficiency in Java, Python, or C#",
        source_text="Strong proficiency in Java, Python, or C#",
        importance_level="HIGH",
        weight=1,
        skill_type="SOFT",
    )
    result = _generate_ids_and_groups(_repair_or_groups([r]))
    assert [x.name for x in result] == ["Java", "Python", "C#"]
    assert len({x.relationship_group for x in result}) == 1
    assert all(x.relationship_operator == "OR" for x in result)
    assert len({x.requirement_id for x in result}) == 3


def test_ids_are_regenerated_in_python():
    from services.jd_parser import _generate_ids_and_groups

    rows = [
        JDRequirement(requirement_id="duplicate", category="EXPERIENCE", name="A"),
        JDRequirement(requirement_id="duplicate", category="EXPERIENCE", name="B"),
    ]
    result = _generate_ids_and_groups(rows)
    assert [x.requirement_id for x in result] == ["req_001", "req_002"]


def test_weight_zero_disables_requirement():
    from services.jd_consistency import normalize_review_values

    assert normalize_review_values("HIGH", 0, "HARD") == ("NOT_REQUIRED", 0, "NONE")


def test_metadata_location_is_not_a_candidate_requirement(monkeypatch):
    from llm.schemas import JDAnalysisSchema, JDRequirementSchema
    from services.jd_parser import parse_jd

    jd = """Position Title: Senior Software Developer\nExperience: 5-7 Years\nLocation: Bengaluru, Karnataka, India / Hybrid\nDepartment: Product Engineering\n\nROLE OVERVIEW\nWe are hiring a senior developer to build web applications.\n"""
    mocked = JDAnalysisSchema(
        job_title="Senior Software Developer",
        requirements=[
            JDRequirementSchema(
                name="Bengaluru location",
                category="LOCATION",
                source_text="Location: Bengaluru, Karnataka, India / Hybrid",
                skill_type="HARD",
            ),
            JDRequirementSchema(
                name="Production web application development",
                category="TECHNICAL_SKILL",
                source_text="build web applications",
                skill_type="SOFT",
            ),
        ],
    )

    monkeypatch.setattr(
        "services.jd_parser.LocalLLM.structured",
        lambda self, *args, **kwargs: mocked,
    )
    result = parse_jd(jd, "test")
    assert not any(r.category.value in {"LOCATION", "WORK_ARRANGEMENT"} for r in result.requirements)


def test_body_location_constraint_is_retained(monkeypatch):
    from llm.schemas import JDAnalysisSchema, JDRequirementSchema
    from services.jd_parser import parse_jd

    jd = """Position Title: Senior Software Developer\nExperience: 5-7 Years\nLocation: Bengaluru\nDepartment: Product Engineering\n\nROLE OVERVIEW\nCandidates must be based in Bangalore and work closely with the local team.\n"""
    mocked = JDAnalysisSchema(
        job_title="Senior Software Developer",
        requirements=[
            JDRequirementSchema(
                name="Candidate must be based in Bangalore",
                category="LOCATION",
                source_text="Candidates must be based in Bangalore",
                skill_type="HARD",
            ),
        ],
    )
    monkeypatch.setattr(
        "services.jd_parser.LocalLLM.structured",
        lambda self, *args, **kwargs: mocked,
    )
    result = parse_jd(jd, "test")
    location_rows = [r for r in result.requirements if r.category.value == "LOCATION"]
    assert len(location_rows) == 1
    assert location_rows[0].source_text == "Candidates must be based in Bangalore"


def test_responsibility_and_success_measure_cannot_be_hard(monkeypatch):
    from llm.schemas import JDAnalysisSchema, JDRequirementSchema
    from services.jd_parser import parse_jd

    jd = """ROLE\nDesign software applications and maintain production quality.\nSuccess in this role: quality and reliability of delivered software.\n"""
    mocked = JDAnalysisSchema(
        requirements=[
            JDRequirementSchema(
                name="Design software applications",
                category="RESPONSIBILITY",
                source_text="Design software applications",
                importance_level="CRITICAL",
                skill_type="HARD",
            ),
            JDRequirementSchema(
                name="Quality and reliability of delivered software",
                category="SUCCESS_MEASURE",
                source_text="quality and reliability of delivered software",
                importance_level="CRITICAL",
                skill_type="HARD",
            ),
        ]
    )
    monkeypatch.setattr(
        "services.jd_parser.LocalLLM.structured",
        lambda self, *args, **kwargs: mocked,
    )
    result = parse_jd(jd, "test")
    assert all(r.skill_type == "SOFT" for r in result.requirements)


def test_preferred_qualification_is_not_a_valid_category():
    import pytest
    from pydantic import ValidationError
    from llm.schemas import JDRequirementSchema

    with pytest.raises(ValidationError):
        JDRequirementSchema(
            name="Docker",
            category="PREFERRED_QUALIFICATION",
            source_text="Experience with Docker",
        )


def test_responsibility_granularity_rejects_duplicate_source_bullet():
    from services.jd_parser import _validate_responsibility_granularity

    jd = """KEY RESPONSIBILITIES
• Manage customer accounts and provide regular reporting.
• Prepare executive presentations.
"""
    rows = [
        JDRequirement(
            requirement_id="1",
            category="RESPONSIBILITY",
            name="Manage customer accounts",
            source_text="Manage customer accounts and provide regular reporting.",
        ),
        JDRequirement(
            requirement_id="2",
            category="RESPONSIBILITY",
            name="Provide regular reporting",
            source_text="Manage customer accounts and provide regular reporting.",
        ),
    ]
    accepted, rejected = _validate_responsibility_granularity(jd, rows)
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert "duplicate source bullet" in rejected[0]


def test_responsibility_granularity_rejects_source_spanning_bullets():
    from services.jd_parser import _validate_responsibility_granularity

    jd = """KEY RESPONSIBILITIES
• Manage customer accounts.
• Prepare executive presentations.
"""
    rows = [
        JDRequirement(
            requirement_id="1",
            category="RESPONSIBILITY",
            name="Manage accounts and prepare presentations",
            source_text="Manage customer accounts. Prepare executive presentations.",
        ),
    ]
    accepted, rejected = _validate_responsibility_granularity(jd, rows)
    assert accepted == []
    assert len(rejected) == 1
    assert "source spans multiple bullets" in rejected[0]


def test_jd_prompt_separates_category_from_source_classification():
    from llm.prompts import JD_SYSTEM

    assert "category describes WHAT KIND of requirement it is" in JD_SYSTEM
    assert "Never use a category such as PREFERRED_QUALIFICATION" in JD_SYSTEM
    assert "Docker" in JD_SYSTEM and "TECHNICAL_SKILL" in JD_SYSTEM
    assert "source_classification=PREFERRED" in JD_SYSTEM


def test_jd_prompt_defines_functional_and_behavioral_boundaries():
    from llm.prompts import JD_SYSTEM

    assert "TECHNICAL_SKILL: a named technology" in JD_SYSTEM
    assert "FUNCTIONAL_SKILL: a role-related practice" in JD_SYSTEM
    assert "BEHAVIORAL: interpersonal or personal working characteristics" in JD_SYSTEM
    assert "written/verbal communication" in JD_SYSTEM


def test_source_bullet_granularity_applies_to_qualifications():
    from services.jd_parser import _validate_source_bullet_granularity

    jd = """REQUIRED QUALIFICATIONS
• Experience with Docker and cloud platforms such as AWS or Azure.
• Experience writing automated tests.
"""
    rows = [
        JDRequirement(
            requirement_id="1",
            category="TECHNICAL_SKILL",
            name="Docker experience",
            source_text="Experience with Docker and cloud platforms such as AWS or Azure.",
        ),
        JDRequirement(
            requirement_id="2",
            category="TECHNICAL_SKILL",
            name="Cloud platform experience",
            source_text="Experience with Docker and cloud platforms such as AWS or Azure.",
        ),
    ]
    accepted, rejected = _validate_source_bullet_granularity(jd, rows)
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert "duplicate source bullet" in rejected[0]


def test_source_bullet_granularity_allows_explicit_or_group():
    from services.jd_parser import _validate_source_bullet_granularity

    jd = """REQUIRED QUALIFICATIONS
• Strong proficiency in Java, Python, or C#.
"""
    rows = [
        JDRequirement(
            requirement_id="1",
            category="TECHNICAL_SKILL",
            name="Java",
            source_text="Strong proficiency in Java, Python, or C#.",
            relationship_group="group_001",
            relationship_operator="OR",
        ),
        JDRequirement(
            requirement_id="2",
            category="TECHNICAL_SKILL",
            name="Python",
            source_text="Strong proficiency in Java, Python, or C#.",
            relationship_group="group_001",
            relationship_operator="OR",
        ),
        JDRequirement(
            requirement_id="3",
            category="TECHNICAL_SKILL",
            name="C#",
            source_text="Strong proficiency in Java, Python, or C#.",
            relationship_group="group_001",
            relationship_operator="OR",
        ),
    ]
    accepted, rejected = _validate_source_bullet_granularity(jd, rows)
    assert len(accepted) == 3
    assert rejected == []


def test_source_bullet_granularity_rejects_cross_section_bullet_merge():
    from services.jd_parser import _validate_source_bullet_granularity

    jd = """PREFERRED QUALIFICATIONS
• Familiarity with CI/CD pipelines.
• Exposure to application monitoring and observability tools.
"""
    rows = [
        JDRequirement(
            requirement_id="1",
            category="TECHNICAL_SKILL",
            name="CI/CD and monitoring",
            source_text="Familiarity with CI/CD pipelines. Exposure to application monitoring and observability tools.",
        ),
    ]
    accepted, rejected = _validate_source_bullet_granularity(jd, rows)
    assert accepted == []
    assert len(rejected) == 1
    assert "source spans multiple bullets" in rejected[0]


def test_jd_prompt_defines_qualification_bullet_granularity():
    from llm.prompts import JD_SYSTEM

    assert "one requirement row per JD bullet" in JD_SYSTEM
    assert "explicit OR alternative list" in JD_SYSTEM
    assert "Docker AND (AWS OR Azure)" in JD_SYSTEM
    assert "Do not decompose a qualification bullet beyond its literal logical" in JD_SYSTEM
