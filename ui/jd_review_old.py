import re
from collections import defaultdict

import streamlit as st

from models.job import JDAnalysis, JDRequirement, JDCategory
from services.jd_consistency import normalize_review_values


IMPORTANCE_OPTIONS = ["NOT_REQUIRED", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
IMPORTANCE_LABELS = {
    "NOT_REQUIRED": "Not Required",
    "LOW": "Low",
    "MEDIUM": "Medium",
    "HIGH": "High",
    "CRITICAL": "Critical",
}
IMPORTANCE_WEIGHTS = {"LOW": 3, "MEDIUM": 5, "HIGH": 8, "CRITICAL": 10}
SKILL_TYPE_OPTIONS = ["NONE", "SOFT", "HARD"]
RELATIONSHIP_OPTIONS = ["NONE", "OR", "AND"]
CATEGORY_OPTIONS = [x.value for x in JDCategory]


def _tier(requirement: JDRequirement) -> str:
    if requirement.skill_type == "HARD":
        return "Must-Have"
    if requirement.skill_type == "SOFT" and requirement.importance_level in {"HIGH", "CRITICAL"}:
        return "Scored"
    return "Nice-to-Have"


def _normalise_duplicate_text(value: str) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _canonical_duplicate_token(token: str) -> str:
    """Lightweight deterministic stemming for duplicate detection.

    This is deliberately conservative and dependency-free. It handles common
    JD variants such as account/accounts and manage/management without making
    the scoring or parsing model dependent on an NLP package.
    """
    token = token.lower().strip()
    if len(token) <= 3:
        return token

    replacements = (
        ("ies", "y"),
        ("ments", ""),
        ("ment", ""),
        ("ations", "ate"),
        ("ation", "ate"),
        ("ing", ""),
        ("ers", ""),
        ("er", ""),
        ("ed", ""),
        ("es", ""),
        ("s", ""),
    )
    for suffix, replacement in replacements:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            candidate = token[:-len(suffix)] + replacement
            if len(candidate) >= 3:
                return candidate
    return token


def _duplicate_tokens(text: str) -> set[str]:
    normalized = _normalise_duplicate_text(text)
    return {
        _canonical_duplicate_token(token)
        for token in normalized.split()
        if len(token) >= 3
    }


def _near_duplicate(a: str, b: str) -> bool:
    a_n = _normalise_duplicate_text(a)
    b_n = _normalise_duplicate_text(b)
    if not a_n or not b_n:
        return False

    if a_n == b_n or a_n in b_n or b_n in a_n:
        return True

    a_tokens, b_tokens = _duplicate_tokens(a), _duplicate_tokens(b)
    if not a_tokens or not b_tokens:
        return False

    overlap = len(a_tokens & b_tokens) / max(1, min(len(a_tokens), len(b_tokens)))
    return overlap >= 0.85


def _duplicate_groups(requirements: list[JDRequirement]) -> list[list[JDRequirement]]:
    """Return unique cross-category near-duplicate groups."""
    rows = list(requirements)
    parent = list(range(len(rows)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, left in enumerate(rows):
        for j in range(i + 1, len(rows)):
            right = rows[j]
            if left.category != right.category and _near_duplicate(left.name, right.name):
                union(i, j)

    components = defaultdict(list)
    for index, req in enumerate(rows):
        components[find(index)].append(req)

    groups = []
    for members in components.values():
        if len(members) >= 2:
            groups.append(sorted(members, key=lambda r: r.requirement_id))

    groups.sort(key=lambda group: min(r.requirement_id for r in group))
    return groups


def _category_weight_breakdown(requirements: list[JDRequirement]) -> list[dict]:
    totals = defaultdict(int)
    for req in requirements:
        totals[req.category.value] += max(0, int(req.weight or 0))

    total_weight = sum(totals.values())
    if total_weight <= 0:
        return []

    return [
        {
            "Category": category,
            "Weight": weight,
            "Percentage": weight / total_weight,
        }
        for category, weight in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    ]


def _render_review_anomalies(requirements: list[JDRequirement]) -> None:
    """Show only actionable rule-based anomalies; weight distribution is informational."""
    duplicate_groups = _duplicate_groups(requirements)
    bad_gates = [
        r for r in requirements
        if r.category in {JDCategory.RESPONSIBILITY, JDCategory.SUCCESS_MEASURE}
        and r.skill_type == "HARD"
    ]

    if not duplicate_groups and not bad_gates:
        st.success("No rule-based review anomalies detected.")
        return

    with st.container(border=True):
        if duplicate_groups:
            st.markdown("**Possible Duplicates:**")
            for number, group in enumerate(duplicate_groups, start=1):
                st.markdown(f"**{number}.**")
                for req in group:
                    st.markdown(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;`{req.requirement_id}` "
                        f"**[{req.category.value}]**: {req.name}"
                    )

        if bad_gates:
            if duplicate_groups:
                st.markdown("---")
            st.markdown("**Responsibility/Success Measure rows marked HARD:**")
            for req in bad_gates:
                st.markdown(
                    f"- `{req.requirement_id}` **[{req.category.value}]**: {req.name}"
                )


def _render_weight_distribution(requirements: list[JDRequirement]) -> None:
    breakdown = _category_weight_breakdown(requirements)

    st.markdown("### JD Weight Distribution")
    st.caption("Informational view of the current recruiter-edited weights. No automatic changes are made.")

    c1, c2 = st.columns([1, 5])
    with c1:
        refresh = st.button(
            "Refresh Distribution",
            key="refresh_weight_distribution",
            help="Recalculate the percentages and chart from the current recruiter-edited weights.",
        )
    if refresh:
        # The tier editors have already rendered by the time this section is
        # reached, so their latest values are available in session state.
        current = st.session_state.get("jd")
        if current is not None:
            for tier, payload in st.session_state.get("jd_tier_edits", {}).items():
                edited, mapping = payload
                current = _apply_visual_rows(current, edited, mapping)

            if st.session_state.get("jd_advanced_view") and "jd_advanced_edit" in st.session_state:
                mapping = {r.requirement_id: [r.requirement_id] for r in current.requirements}
                current = _apply_visual_rows(current, st.session_state["jd_advanced_edit"], mapping)

            st.session_state["jd"] = current
            st.session_state["jd_dirty"] = True
            st.session_state["weight_distribution_refreshed"] = True
            st.rerun()

    if not breakdown:
        st.caption("No weighted requirements are currently defined.")
        return

    line = " | ".join(
        f"**{item['Category']}** {item['Percentage']:.0%}"
        for item in breakdown
    )
    st.markdown(line)

    chart_data = [
        {"Category": item["Category"], "Weight": item["Weight"]}
        for item in breakdown
    ]

    st.vega_lite_chart(
        chart_data,
        {
            "width": "container",
            "height": 320,
            "mark": {"type": "arc", "innerRadius": 45},
            "encoding": {
                "theta": {"field": "Weight", "type": "quantitative"},
                "color": {"field": "Category", "type": "nominal"},
                "tooltip": [
                    {"field": "Category", "type": "nominal"},
                    {"field": "Weight", "type": "quantitative"},
                ],
            },
        },
    )

def _group_members(requirements: list[JDRequirement]):
    groups = defaultdict(list)
    for req in requirements:
        if req.relationship_group and req.relationship_operator == "OR":
            groups[req.relationship_group].append(req)
    return groups


def _build_visual_rows(requirements, tier, expanded_groups):
    groups = _group_members(requirements)
    consumed = set()
    rows = []
    mapping = {}

    for req in requirements:
        if _tier(req) != tier or req.requirement_id in consumed:
            continue

        group = req.relationship_group if req.relationship_operator == "OR" else None
        if group and group in groups:
            members = [m for m in groups[group] if _tier(m) == tier]
            if not members:
                continue
            if group in expanded_groups:
                for member in members:
                    rows.append(_row_from_requirement(member, member.requirement_id))
                    mapping[member.requirement_id] = [member.requirement_id]
                    consumed.add(member.requirement_id)
            else:
                display_id = group
                rows.append(_row_from_requirement(
                    members[0],
                    display_id,
                    requirement_name=" OR ".join(m.name for m in members),
                    group_display=group,
                    operator_display="OR",
                ))
                mapping[display_id] = [m.requirement_id for m in members]
                consumed.update(m.requirement_id for m in members)
            continue

        rows.append(_row_from_requirement(req, req.requirement_id))
        mapping[req.requirement_id] = [req.requirement_id]
        consumed.add(req.requirement_id)

    return rows, mapping


def _row_from_requirement(req, display_id, requirement_name=None, group_display=None, operator_display=None):
    return {
        "ID": display_id,
        "Category": req.category.value,
        "Requirement": requirement_name if requirement_name is not None else req.name,
        "Importance": IMPORTANCE_LABELS.get(req.importance_level, "Medium"),
        "Weight": req.weight,
        "Min Years": req.minimum_years,
        "Threshold": req.minimum_threshold or "",
        "Group": group_display if group_display is not None else (req.relationship_group or ""),
        "Operator": operator_display if operator_display is not None else req.relationship_operator,
        "Skill Type": req.skill_type,
    }


def _render_bulk_controls(analysis: JDAnalysis, tier: str):
    tier_requirements = [r for r in analysis.requirements if _tier(r) == tier]
    categories = sorted({r.category.value for r in tier_requirements})
    if not categories:
        return

    st.markdown("**Bulk edit category**")
    c1, c2, c3, c4 = st.columns([1.4, 1.1, 1.1, 1])
    with c1:
        category = st.selectbox(
            "Category",
            categories,
            key=f"bulk_category_{tier}",
            label_visibility="collapsed",
        )
    with c2:
        importance_label = st.selectbox(
            "Importance",
            [IMPORTANCE_LABELS[x] for x in IMPORTANCE_OPTIONS],
            index=0,
            key=f"bulk_importance_{tier}",
            label_visibility="collapsed",
        )
    with c3:
        skill_type = st.selectbox(
            "Skill Type",
            SKILL_TYPE_OPTIONS,
            key=f"bulk_skill_{tier}",
            label_visibility="collapsed",
        )
    with c4:
        if st.button("Apply to category", key=f"bulk_apply_{tier}"):
            reverse = {v: k for k, v in IMPORTANCE_LABELS.items()}
            importance = reverse[importance_label]
            for req in analysis.requirements:
                if _tier(req) != tier or req.category.value != category:
                    continue
                if importance == "NOT_REQUIRED":
                    req.importance_level, req.weight, req.skill_type = "NOT_REQUIRED", 0, "NONE"
                else:
                    req.importance_level = importance
                    req.weight = IMPORTANCE_WEIGHTS[importance]
                    req.skill_type = skill_type
                    if req.category in {JDCategory.RESPONSIBILITY, JDCategory.SUCCESS_MEASURE} and req.skill_type == "HARD":
                        req.skill_type = "SOFT"
            st.session_state["jd"] = analysis
            st.session_state["jd_dirty"] = True
            st.rerun()


def _render_group_toggles(requirements, tier):
    groups = _group_members(requirements)
    tier_groups = [
        group for group, members in groups.items()
        if any(_tier(m) == tier for m in members)
    ]
    expanded = set()
    for group in tier_groups:
        members = [m for m in groups[group] if _tier(m) == tier]
        label = f"{group}: " + " OR ".join(m.name for m in members)
        if st.checkbox(
            f"Edit individually — {label}",
            key=f"edit_group_{group}",
            help="Expand this OR group so each alternative can be edited separately.",
        ):
            expanded.add(group)
    return expanded


def _edited_rows(edited):
    """Yield editor rows from either a DataFrame or list-of-dicts."""
    if edited is None:
        return []
    if hasattr(edited, "iterrows"):
        return (row for _, row in edited.iterrows())
    if isinstance(edited, list):
        return iter(edited)
    if isinstance(edited, tuple):
        return iter(edited)
    if isinstance(edited, dict):
        return iter([edited])
    return iter([])


def _apply_visual_rows(analysis: JDAnalysis, edited, mapping):
    by_id = {r.requirement_id: r for r in analysis.requirements}
    reverse_labels = {value: key for key, value in IMPORTANCE_LABELS.items()}

    for row in _edited_rows(edited):
        display_id = str(row.get("ID", "")).strip()
        member_ids = mapping.get(display_id, [])
        if not member_ids:
            continue

        importance = reverse_labels.get(str(row.get("Importance", "Medium")), "MEDIUM")
        skill_type = str(row.get("Skill Type", "SOFT")).upper()
        weight_value = row.get("Weight", 0)
        importance, weight, skill_type = normalize_review_values(importance, weight_value, skill_type)

        category = str(row.get("Category", "OTHER")).upper()
        if category not in CATEGORY_OPTIONS:
            category = "OTHER"

        min_years = row.get("Min Years")
        try:
            min_years = None if min_years in (None, "") else float(min_years)
        except (TypeError, ValueError):
            min_years = None

        threshold = str(row.get("Threshold", "")).strip() or None
        operator = str(row.get("Operator", "NONE")).upper()
        if operator not in RELATIONSHIP_OPTIONS:
            operator = "NONE"

        # A collapsed OR group is one visual row; edits apply to every member.
        for member_id in member_ids:
            req = by_id[member_id]
            req.category = category
            req.importance_level = importance
            req.weight = weight
            req.skill_type = skill_type
            req.minimum_years = min_years
            req.minimum_threshold = threshold
            if len(member_ids) > 1:
                req.relationship_operator = "OR"
            else:
                req.relationship_operator = operator

    analysis.requirements = list(by_id.values())
    return analysis


def _render_tier(analysis: JDAnalysis, tier: str, expanded: bool):
    with st.expander(tier, expanded=expanded):
        _render_bulk_controls(analysis, tier)
        expanded_groups = _render_group_toggles(analysis.requirements, tier)
        rows, mapping = _build_visual_rows(analysis.requirements, tier, expanded_groups)
        if not rows:
            st.caption("No requirements in this tier.")
            return analysis

        edited = st.data_editor(
            rows,
            hide_index=True,
            num_rows="fixed",
            height=760,
            width="stretch",
            column_config={
                "ID": st.column_config.TextColumn(disabled=True),
                "Category": st.column_config.SelectboxColumn(options=CATEGORY_OPTIONS),
                "Requirement": st.column_config.TextColumn(disabled=True),
                "Importance": st.column_config.SelectboxColumn(options=[IMPORTANCE_LABELS[x] for x in IMPORTANCE_OPTIONS]),
                "Weight": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                "Min Years": st.column_config.NumberColumn(min_value=0, step=0.5),
                "Threshold": st.column_config.TextColumn(),
                "Group": st.column_config.TextColumn(disabled=True),
                "Operator": st.column_config.SelectboxColumn(options=RELATIONSHIP_OPTIONS, disabled=True),
                "Skill Type": st.column_config.SelectboxColumn(options=SKILL_TYPE_OPTIONS),
            },
            key=f"jd_review_{tier.lower().replace('-', '_')}",
        )
        st.session_state.setdefault("jd_tier_edits", {})[tier] = (edited, mapping)
    return analysis


def render_jd_review(analysis: JDAnalysis):
    st.subheader("Review Extracted Evaluation Model")
    st.caption("AI extracts only criteria supported by the JD. Not Required is a recruiter override.")

    if analysis.summary:
        st.info(analysis.summary)
    if analysis.rejected_requirements:
        review_notes = [
            item for item in analysis.rejected_requirements
            if str(item).startswith("[REVIEW]")
        ]
        actual_rejected = [
            item for item in analysis.rejected_requirements
            if not str(item).startswith("[REVIEW]")
        ]

        if actual_rejected:
            st.warning(
                "Some AI-extracted rows were rejected during validation: "
                + ", ".join(actual_rejected)
            )
        if review_notes:
            st.info(
                "Review notes (requirements retained): "
                + "; ".join(str(item).removeprefix("[REVIEW] ") for item in review_notes)
            )

    _render_review_anomalies(analysis.requirements)

    st.markdown("### Tiered review")
    st.caption("Must-Have = HARD. Scored = HIGH/CRITICAL SOFT. Nice-to-Have = everything else.")

    _render_tier(analysis, "Must-Have", True)
    _render_tier(analysis, "Scored", False)
    _render_tier(analysis, "Nice-to-Have", False)

    st.markdown("### Advanced view")
    advanced = st.toggle("Show full flat requirement table", value=False, key="jd_advanced_view")
    if advanced:
        rows = [_row_from_requirement(r, r.requirement_id) for r in analysis.requirements]
        edited = st.data_editor(
            rows,
            hide_index=True,
            num_rows="fixed",
            height=760,
            width="stretch",
            column_config={
                "ID": st.column_config.TextColumn(disabled=True),
                "Category": st.column_config.SelectboxColumn(options=CATEGORY_OPTIONS),
                "Requirement": st.column_config.TextColumn(),
                "Importance": st.column_config.SelectboxColumn(options=[IMPORTANCE_LABELS[x] for x in IMPORTANCE_OPTIONS]),
                "Weight": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                "Min Years": st.column_config.NumberColumn(min_value=0, step=0.5),
                "Threshold": st.column_config.TextColumn(),
                "Group": st.column_config.TextColumn(),
                "Operator": st.column_config.SelectboxColumn(options=RELATIONSHIP_OPTIONS),
                "Skill Type": st.column_config.SelectboxColumn(options=SKILL_TYPE_OPTIONS),
            },
            key="jd_review_advanced",
        )
        st.session_state["jd_advanced_edit"] = edited

    _render_weight_distribution(analysis.requirements)

    with st.expander("Source evidence and JD classification", expanded=False):
        for r in analysis.requirements:
            st.markdown(f"**{r.requirement_id} — {r.name}**")
            st.caption(
                f"JD classification: {r.source_classification.value} | "
                f"Section: {r.source_section_heading or 'Not specified'}"
            )
            st.write(r.source_text or "No source evidence captured.")

    if st.button("Apply JD Review", type="primary"):
        # Prefer Advanced view if the recruiter explicitly used it. Otherwise
        # merge edits from each tiered table. The underlying list remains flat.
        if st.session_state.get("jd_advanced_view") and "jd_advanced_edit" in st.session_state:
            mapping = {r.requirement_id: [r.requirement_id] for r in analysis.requirements}
            analysis = _apply_visual_rows(analysis, st.session_state["jd_advanced_edit"], mapping)
        else:
            tier_edits = st.session_state.get("jd_tier_edits", {})
            for tier, payload in tier_edits.items():
                edited, mapping = payload
                analysis = _apply_visual_rows(analysis, edited, mapping)

        ids = [r.requirement_id for r in analysis.requirements]
        if len(ids) != len(set(ids)):
            st.error("Duplicate requirement IDs detected. The review was not applied.")
            return analysis

        # Final UI-layer safety normalization.
        for req in analysis.requirements:
            req.importance_level, req.weight, req.skill_type = normalize_review_values(
                req.importance_level, req.weight, req.skill_type
            )
            if req.category in {JDCategory.RESPONSIBILITY, JDCategory.SUCCESS_MEASURE} and req.skill_type == "HARD":
                req.skill_type = "SOFT"

        st.session_state["jd"] = analysis
        st.session_state["jd_dirty"] = True
        st.session_state["jd_approved_pending_save"] = True
        st.success(f"Applied {len(analysis.requirements)} JD evaluation criteria.")
        st.rerun()

    return analysis
