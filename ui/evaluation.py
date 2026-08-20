import streamlit as st
from database.repositories import update_recruiter_decision

def render_evaluation(result, editable=True):
    st.header(f"{result.evaluation_number} — {result.job_title}")
    st.metric("Final Score", f"{result.final_score:.1f} / 100")
    a, b, c = st.columns(3)
    a.metric("Base", f"{result.base_score:.1f}")
    b.metric("Keyword", f"{result.keyword_adjustment:+.1f}")
    c.metric("Gate", result.gate_status)

    st.write(f"**Candidate:** {result.candidate_name}")
    st.write(f"**Email:** {result.candidate_email}")
    st.write(f"**Recommendation:** {result.recommendation}")

    with st.expander("Requirement Breakdown", expanded=True):
        for m in result.requirement_matches:
            st.markdown(f"### {m.requirement_name} — {m.status}")
            st.write(f"Confidence: {m.confidence:.2f}")
            if m.evidence_text:
                st.caption(m.evidence_text)
            st.write(m.explanation)

    with st.expander("Keyword Signals"):
        for k in result.keyword_detections:
            st.write(
                f"{k.keyword} | {k.signal_type} | "
                f"detected={k.detected} | "
                f"adjustment={k.applied_adjustment:+.1f}"
            )
            if k.context:
                st.caption(k.context)

    if result.contradictions:
        st.subheader("Contradictions")
        for item in result.contradictions:
            st.warning(item)

    st.subheader("Strengths")
    for item in result.strengths:
        st.write("• " + item)

    st.subheader("Gaps")
    for item in result.gaps:
        st.write("• " + item)

    if editable:
        decision = st.selectbox(
            "Recruiter Decision",
            ["", "Shortlist", "Review", "Reject", "Hold"],
            key="decision_" + result.evaluation_number,
        )
        notes = st.text_area(
            "Recruiter Notes",
            key="notes_" + result.evaluation_number,
        )
        if st.button(
            "Save Recruiter Decision",
            key="save_" + result.evaluation_number,
        ):
            update_recruiter_decision(
                result.evaluation_number,
                decision,
                notes,
            )
            st.success("Recruiter decision saved.")
