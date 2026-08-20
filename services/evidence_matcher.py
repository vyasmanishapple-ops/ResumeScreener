from llm.client import LocalLLM
from llm.prompts import MATCH_SYSTEM
from llm.schemas import MatchSchema
from models.evidence import RequirementMatch, VALID_STATUSES


STATUS_ALIASES = {
    "SATISFIED": "EXPLICIT_MATCH",
    "MATCH": "EXPLICIT_MATCH",
    "MATCHED": "EXPLICIT_MATCH",
    "FULL_MATCH": "EXPLICIT_MATCH",
    "STRONG_MATCH": "EXPLICIT_MATCH",

    "PARTIALLY_SATISFIED": "PARTIAL_MATCH",
    "PARTIAL": "PARTIAL_MATCH",
    "PARTIAL_MATCHED": "PARTIAL_MATCH",

    "RELATED": "RELATED_EVIDENCE",
    "RELATED_MATCH": "RELATED_EVIDENCE",

    "NOT_SATISFIED": "NO_EVIDENCE",
    "NOT_FOUND": "NO_EVIDENCE",
    "MISSING": "NO_EVIDENCE",
    "NO_MATCH": "NO_EVIDENCE",

    "CONTRADICTION": "CONTRADICTED",
    "CONFLICT": "CONTRADICTED",
}


def normalize_status(status: str) -> str:
    """
    Convert common LLM status variants into the application's
    canonical evidence status vocabulary.
    """

    normalized = (
        status.strip()
        .upper()
        .replace("-", "_")
        .replace(" ", "_")
    )

    return STATUS_ALIASES.get(
        normalized,
        normalized,
    )


def match_requirement(
    requirement,
    candidate,
    model=None,
):
    evidence = "\n".join(
        f"[{item.source_section}] "
        f"{item.evidence_text}"
        for item in candidate.evidence
    )

    result = LocalLLM(model).structured(
        MatchSchema,
        MATCH_SYSTEM,
        (
            "REQUIREMENT:\n"
            + requirement.model_dump_json()
            + "\n\nCANDIDATE EVIDENCE:\n"
            + evidence
        ),
    )

    raw_data = result.model_dump()

    raw_status = raw_data.get(
        "status",
        "",
    )

    canonical_status = normalize_status(
        raw_status
    )

    if canonical_status not in VALID_STATUSES:
        raise ValueError(
            "Invalid LLM match status: "
            f"{raw_status}. "
            f"Normalized value: {canonical_status}"
        )

    raw_data["status"] = canonical_status

    return RequirementMatch.model_validate(
        raw_data
    )