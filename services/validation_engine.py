VALID = {
    "EXPLICIT_MATCH","PARTIAL_MATCH","RELATED_EVIDENCE",
    "NO_EVIDENCE","CONTRADICTED"
}

def validate(requirements, matches, score):
    errors = []
    if len(requirements) != len(matches):
        errors.append("Requirement/match count mismatch")
    if not 0 <= score["final_score"] <= 100:
        errors.append("Final score outside 0-100")
    for match in matches:
        if match.status not in VALID:
            errors.append(f"Invalid status: {match.status}")
    return errors
