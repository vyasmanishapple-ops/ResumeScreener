from pathlib import Path
from collections import defaultdict
import yaml


STATUS_VALUES = {
    "EXPLICIT_MATCH": 1.0,
    "PARTIAL_MATCH": 0.7,
    "RELATED_EVIDENCE": 0.4,
    "NO_EVIDENCE": 0.0,
    "CONTRADICTED": 0.0,
}


def load_config():
    return yaml.safe_load(Path("config/scoring.yaml").read_text(encoding="utf-8"))


def _requirement_value(match):
    return STATUS_VALUES.get(match.status, 0.0)


def _group_scores(requirements, matches):
    groups = defaultdict(list)
    for requirement, match in zip(requirements, matches):
        key = requirement.relationship_group or f"__single__{requirement.requirement_id}"
        groups[key].append((requirement, match))

    values = {}
    for _group, members in groups.items():
        operators = {
            r.relationship_operator
            for r, _m in members
            if r.relationship_operator != "NONE"
        }
        operator = "OR" if "OR" in operators else "AND" if "AND" in operators else "NONE"

        if operator == "OR":
            best_value = max(_requirement_value(m) for _r, m in members)
            for requirement, _match in members:
                values[requirement.requirement_id] = best_value
        else:
            for requirement, match in members:
                values[requirement.requirement_id] = _requirement_value(match)
    return values


def calculate_score(requirements, matches, keyword_detections):
    config = load_config()
    values = _group_scores(requirements, matches)

    scored_requirements = [
        r for r in requirements
        if r.importance_level != "NOT_REQUIRED" and r.weight > 0
    ]

    total_weight = sum(r.weight for r in scored_requirements)
    weighted = sum(
        values.get(r.requirement_id, 0.0) * r.weight
        for r in scored_requirements
    )
    base = weighted / total_weight * 100 if total_weight else 0.0

    raw_adjustment = sum(
        d.applied_adjustment
        for d in keyword_detections
        if d.signal_type in {"POSITIVE", "NEGATIVE"}
    )
    limits = config["keyword_limits"]
    adjustment = max(
        limits["maximum_negative_adjustment"],
        min(limits["maximum_positive_adjustment"], raw_adjustment),
    )

    final = max(0, min(100, base + adjustment))

    failed = [
        r.name
        for r, match in zip(requirements, matches)
        if r.skill_type == "HARD"
        and r.importance_level != "NOT_REQUIRED"
        and match.status in {"NO_EVIDENCE", "CONTRADICTED"}
    ]

    if failed:
        gate = "FAILED"
        recommendation = config["gates"]["failed_gate_recommendation"]
    elif final >= config["thresholds"]["strong_shortlist"]:
        gate = "PASSED"
        recommendation = "STRONG SHORTLIST"
    elif final >= config["thresholds"]["shortlist"]:
        gate = "PASSED"
        recommendation = "SHORTLIST"
    elif final >= config["thresholds"]["review"]:
        gate = "PASSED"
        recommendation = "REVIEW"
    else:
        gate = "PASSED"
        recommendation = "REJECT"

    return {
        "base_score": round(base, 2),
        "keyword_adjustment": round(adjustment, 2),
        "final_score": round(final, 2),
        "gate_status": gate,
        "recommendation": recommendation,
        "failed_gates": failed,
    }
