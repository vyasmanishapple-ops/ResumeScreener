from models.job import JDRequirement
from ui.jd_review import _duplicate_groups, _category_weight_breakdown


def _req(req_id, category, name, weight=5):
    return JDRequirement(
        requirement_id=req_id,
        category=category,
        name=name,
        weight=weight,
    )


def test_duplicate_groups_are_unique_and_cross_category():
    requirements = [
        _req("req_026", "EDUCATION", "Bachelor degree in Computer Science"),
        _req("req_041", "QUALIFICATION", "Bachelor degree in Computer Science"),
        _req("req_042", "RESPONSIBILITY", "Manage customer accounts"),
        _req("req_049", "FUNCTIONAL_SKILL", "Customer account management"),
    ]

    groups = _duplicate_groups(requirements)

    assert len(groups) == 2
    assert {r.requirement_id for r in groups[0]} == {"req_026", "req_041"}
    assert {r.requirement_id for r in groups[1]} == {"req_042", "req_049"}

    all_ids = [r.requirement_id for group in groups for r in group]
    assert len(all_ids) == len(set(all_ids))


def test_weight_breakdown_returns_category_percentages():
    requirements = [
        _req("req_001", "TECHNICAL_SKILL", "Python", 8),
        _req("req_002", "TECHNICAL_SKILL", "REST APIs", 8),
        _req("req_003", "EXPERIENCE", "5 years", 4),
    ]

    breakdown = _category_weight_breakdown(requirements)
    percentages = {row["Category"]: row["Percentage"] for row in breakdown}

    assert percentages["TECHNICAL_SKILL"] == 16 / 20
    assert percentages["EXPERIENCE"] == 4 / 20
    assert sum(percentages.values()) == 1
