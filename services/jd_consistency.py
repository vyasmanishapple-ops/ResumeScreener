IMPORTANCE_WEIGHTS = {"LOW": 3, "MEDIUM": 5, "HIGH": 8, "CRITICAL": 10}


def normalize_review_values(importance, weight, skill_type):
    importance = str(importance or "MEDIUM").upper().replace(" ", "_")
    skill_type = str(skill_type or "SOFT").upper()
    try:
        weight = max(0, min(10, int(weight)))
    except (TypeError, ValueError):
        weight = 0

    if importance == "NOT_REQUIRED" or weight == 0:
        return "NOT_REQUIRED", 0, "NONE"

    if importance not in IMPORTANCE_WEIGHTS:
        importance = "MEDIUM"
    if skill_type not in {"HARD", "SOFT", "NONE"}:
        skill_type = "SOFT"
    return importance, weight, skill_type
