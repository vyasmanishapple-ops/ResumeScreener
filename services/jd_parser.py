import re
from collections import defaultdict
from typing import Iterable

from llm.client import LocalLLM
from llm.prompts import JD_SYSTEM
from llm.schemas import JDAnalysisSchema
from models.job import JDAnalysis, JDRequirement, SourceClassification, JDCategory


IMPORTANCE_WEIGHTS = {
    "LOW": 3,
    "MEDIUM": 5,
    "HIGH": 8,
    "CRITICAL": 10,
}


def _normalise_text(value: str) -> str:
    text = str(value or "")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _metadata_block_text(jd_text: str, max_lines: int = 8) -> str:
    """Return the opening posting-metadata block, excluding the JD body."""
    lines = str(jd_text or "").splitlines()
    metadata_keys = (
        "position title", "job title", "title", "experience", "years of experience",
        "location", "department", "business unit", "team", "function", "employment type",
        "work arrangement", "job type", "requisition", "job id", "reference",
    )
    collected = []
    seen_metadata = False
    for raw in lines[:max_lines]:
        line = raw.strip()
        if not line:
            if collected and seen_metadata:
                break
            continue
        lower = line.lower()
        if any(lower.startswith(key + ":") or lower.startswith(key + " -") for key in metadata_keys):
            collected.append(line)
            seen_metadata = True
            continue
        # A conventional section heading marks the start of the body.
        if (line.isupper() and len(line) <= 80) or lower.endswith(":"):
            break
        if seen_metadata:
            break
        # If the document starts directly with prose, there is no metadata block.
        break
    return "\n".join(collected)


def _source_is_in_metadata_header(jd_text: str, source_text: str) -> bool:
    metadata = _normalise_text(_metadata_block_text(jd_text))
    source = _normalise_text(source_text)
    if not metadata or not source:
        return False
    return source in metadata


def _source_is_supported(jd_text: str, source_text: str) -> bool:
    source = _normalise_text(source_text)
    jd = _normalise_text(jd_text)
    if not source or len(source) < 3:
        return False
    if source in jd:
        return True
    # Light punctuation normalization for legitimate copied text variations.
    compact_source = re.sub(r"[^a-z0-9+/#.]+", " ", source)
    compact_jd = re.sub(r"[^a-z0-9+/#.]+", " ", jd)
    compact_source = re.sub(r"\s+", " ", compact_source).strip()
    compact_jd = re.sub(r"\s+", " ", compact_jd).strip()
    return compact_source in compact_jd


def normalize_importance(requirement):
    level = str(requirement.importance_level or "MEDIUM").strip().upper()
    if level in {"NOT REQUIRED", "NOT_REQUIRED", "OPTIONAL"}:
        # AI is not allowed to emit this. Treat malformed AI output as LOW,
        # while the recruiter UI remains the only place that can set it.
        level = "LOW"
    aliases = {"PREFERRED": "LOW"}
    level = aliases.get(level, level)
    if level not in IMPORTANCE_WEIGHTS:
        level = "MEDIUM"
    requirement.importance_level = level
    requirement.weight = IMPORTANCE_WEIGHTS[level]
    return requirement


def normalize_skill_type(requirement):
    value = str(requirement.skill_type or "SOFT").strip().upper()
    aliases = {"MANDATORY": "HARD", "REQUIRED": "SOFT", "PREFERRED": "SOFT"}
    value = aliases.get(value, value)
    if value not in {"HARD", "SOFT", "NONE"}:
        value = "SOFT"
    if requirement.source_classification == SourceClassification.PREFERRED and value == "HARD":
        value = "SOFT"
    # Duties and outcomes are not objective deal-breakers.
    if requirement.category in {JDCategory.RESPONSIBILITY, JDCategory.SUCCESS_MEASURE} and value == "HARD":
        value = "SOFT"
    requirement.skill_type = value
    return requirement


def normalize_relationship(requirement):
    operator = str(requirement.relationship_operator or "NONE").strip().upper()
    requirement.relationship_operator = operator if operator in {"AND", "OR", "NONE"} else "NONE"
    return requirement


def _split_simple_or_terms(name: str, source_text: str) -> list[str]:
    """Split common flat OR lists while avoiding nested Boolean expressions."""
    phrase = (source_text or name or "").strip()
    if re.search(r"\band\b", phrase, flags=re.I):
        return []

    # Common form: "at least one of A, B, C, or D".
    match = re.search(r"\b(?:at least one of|one of)\s+(.+?)(?:[.;]|$)", phrase, flags=re.I)
    if match:
        candidate = match.group(1)
        parts = re.split(r"\s*,\s*|\s+or\s+", candidate, flags=re.I)
    else:
        # Flat form: "A or B or C" or "A, B, or C".
        parts = re.split(r"\s+or\s+|\s*,\s*(?=[^,]+$)", phrase, flags=re.I)
        if len(parts) < 2:
            return []
        # For comma lists, preserve the comma-separated items and split a final "or".
        if "," in phrase:
            tail = []
            for item in re.split(r"\s*,\s*", phrase):
                tail.extend(re.split(r"\s+or\s+", item, flags=re.I))
            parts = tail

    parts = [p.strip(" ,.;:") for p in parts if p.strip(" ,.;:")]
    parts = [re.sub(r"^or\s+", "", p, flags=re.I).strip() for p in parts]
    if len(parts) < 2:
        return []

    # Strip shared lead-in from the first item only.
    parts[0] = re.sub(
        r"^(strong proficiency in|strong experience with|experience with relational databases such as|experience with|experience in|proficiency in|familiarity with|such as|relational databases such as)\s+",
        "",
        parts[0],
        flags=re.I,
    ).strip()
    if any(len(p.split()) > 8 for p in parts):
        return []
    return parts


def _repair_or_groups(requirements: Iterable[JDRequirement]) -> list[JDRequirement]:
    repaired: list[JDRequirement] = []
    group_counter = 1
    for req in requirements:
        alternatives = _split_simple_or_terms(req.name, req.source_text)
        already_grouped = bool(req.relationship_group and req.relationship_operator == "OR")
        if len(alternatives) >= 2 and not already_grouped:
            group = f"group_{group_counter:03d}"
            group_counter += 1
            for alternative in alternatives:
                clone = req.model_copy(deep=True)
                clone.name = alternative
                clone.relationship_group = group
                clone.relationship_operator = "OR"
                repaired.append(clone)
        else:
            repaired.append(req)
    return repaired


def _generate_ids_and_groups(requirements: list[JDRequirement]) -> list[JDRequirement]:
    group_map: dict[str, str] = {}
    next_group = 1
    for req in requirements:
        original = req.relationship_group
        if original:
            key = str(original)
            if key not in group_map:
                group_map[key] = f"group_{next_group:03d}"
                next_group += 1
            req.relationship_group = group_map[key]
        else:
            req.relationship_group = None
    for index, req in enumerate(requirements, start=1):
        req.requirement_id = f"req_{index:03d}"
        req.parent_requirement_id = None
    return requirements


def _validate_unique(requirements: list[JDRequirement]) -> None:
    ids = [r.requirement_id for r in requirements]
    if len(ids) != len(set(ids)):
        raise ValueError("JD parser generated duplicate requirement IDs")


def _normalize_category(value) -> JDCategory:
    try:
        return JDCategory(value)
    except ValueError:
        return JDCategory.OTHER


def _jd_bullets(jd_text: str) -> list[str]:
    """Return all bullet-point source lines in the JD body."""
    bullets = []
    metadata = _normalise_text(_metadata_block_text(jd_text))
    for raw in str(jd_text or "").splitlines():
        line = raw.strip()
        if not re.match(r"^(?:[-*•▪◦‣]|\d+[.)])\s+", line):
            continue
        bullet = re.sub(r"^(?:[-*•▪◦‣]|\d+[.)])\s+", "", line).strip()
        # Do not treat a bullet embedded in the opening posting metadata as
        # candidate evidence.
        if metadata and _normalise_text(bullet) in metadata:
            continue
        bullets.append(bullet)
    return bullets


def _responsibility_bullets(jd_text: str) -> list[str]:
    """Backward-compatible alias used by existing tests/callers."""
    return _jd_bullets(jd_text)


def _source_bullet_matches(jd_text: str, source_text: str) -> list[int]:
    source = _normalise_text(source_text)
    if not source:
        return []
    matches = []
    for index, bullet in enumerate(_jd_bullets(jd_text)):
        normalized_bullet = _normalise_text(bullet)
        if source in normalized_bullet or normalized_bullet in source:
            matches.append(index)
    return matches


def _responsibility_bullet_index(jd_text: str, source_text: str) -> list[int]:
    return _source_bullet_matches(jd_text, source_text)


def _is_explicit_or_group(requirement: JDRequirement) -> bool:
    return bool(requirement.relationship_group) and str(
        requirement.relationship_operator or ""
    ).upper() == "OR"


def _validate_source_bullet_granularity(
    jd_text: str,
    requirements: list[JDRequirement],
) -> tuple[list[JDRequirement], list[str]]:
    """Validate requirement-to-bullet mapping across JD sections.

    Default rule: one source bullet maps to one requirement. The deliberate
    exception is an explicit OR group, where one bullet may expand into
    multiple atomic alternatives. A requirement whose source spans multiple
    bullets is rejected because it merges separate JD bullets.
    """
    bullets = _jd_bullets(jd_text)
    if not bullets:
        return requirements, []

    accepted: list[JDRequirement] = []
    rejected: list[str] = []
    bullet_members: dict[int, list[JDRequirement]] = defaultdict(list)

    for req in requirements:
        matches = _source_bullet_matches(jd_text, req.source_text)
        if len(matches) > 1:
            rejected.append(
                f"[REVIEW] {req.name or req.source_text} "
                f"[{req.category.value}: source spans multiple bullets]"
            )
            continue
        if len(matches) == 0:
            # Not every valid JD criterion is written as a bullet. Keep prose
            # requirements and let the source-text validator remain the guard.
            accepted.append(req)
            continue
        bullet_members[matches[0]].append(req)

    for members in bullet_members.values():
        if len(members) == 1:
            accepted.append(members[0])
            continue

        # Multiple rows from one bullet are valid only when they form the same
        # explicit OR group. This is the intentional Boolean expansion case.
        groups = {m.relationship_group for m in members}
        all_or = all(_is_explicit_or_group(m) for m in members)
        same_or_group = len(groups) == 1 and None not in groups
        if all_or and same_or_group:
            accepted.extend(members)
            continue

        # Keep the first deterministic row and reject the additional rows.
        accepted.append(members[0])
        for req in members[1:]:
            rejected.append(
                f"[REVIEW] {req.name or req.source_text} "
                f"[{req.category.value}: duplicate source bullet]"
            )

    return accepted, rejected


def _validate_responsibility_granularity(
    jd_text: str,
    requirements: list[JDRequirement],
) -> tuple[list[JDRequirement], list[str]]:
    """Backward-compatible responsibility-specific validation wrapper."""
    responsibility = [
        r for r in requirements if r.category == JDCategory.RESPONSIBILITY
    ]
    others = [
        r for r in requirements if r.category != JDCategory.RESPONSIBILITY
    ]
    accepted_resp, rejected = _validate_source_bullet_granularity(
        jd_text, responsibility
    )
    return others + accepted_resp, rejected

def parse_jd(text, model=None):
    result = LocalLLM(model).structured(
        JDAnalysisSchema,
        JD_SYSTEM,
        "JOB DESCRIPTION:\n" + text,
    )

    analysis = JDAnalysis.model_validate(result.model_dump())
    valid_requirements: list[JDRequirement] = []
    rejected: list[str] = []

    for requirement in analysis.requirements:
        source = str(requirement.source_text or "").strip()
        if not _source_is_supported(text, source):
            rejected.append(requirement.name or source or "Unnamed requirement")
            continue

        requirement.category = _normalize_category(requirement.category)
        # Posting metadata is not itself a candidate constraint. Location and
        # work-arrangement rows must be supported by the JD body, not the
        # opening title/experience/location/department block.
        if requirement.category in {JDCategory.LOCATION, JDCategory.WORK_ARRANGEMENT} and _source_is_in_metadata_header(text, source):
            rejected.append(requirement.name or source or "Metadata-only location/work arrangement")
            continue
        if requirement.source_classification not in SourceClassification:
            requirement.source_classification = SourceClassification.REQUIRED
        normalize_importance(requirement)
        normalize_relationship(requirement)
        normalize_skill_type(requirement)
        valid_requirements.append(requirement)

    # Repair simple OR lists before source-bullet validation so the validator
    # can recognize the intentional one-bullet -> many-row exception.
    repaired = _repair_or_groups(valid_requirements)

    repaired, granularity_rejected = _validate_source_bullet_granularity(
        text, repaired
    )
    rejected.extend(granularity_rejected)

    repaired = _generate_ids_and_groups(repaired)
    _validate_unique(repaired)

    analysis.requirements = repaired
    analysis.rejected_requirements = rejected
    return analysis
