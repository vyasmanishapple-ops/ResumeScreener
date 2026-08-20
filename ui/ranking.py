import streamlit as st

def render_ranking(results):
    st.subheader("Candidate Ranking")
    ordered = sorted(
        results,
        key=lambda item: item.final_score,
        reverse=True,
    )
    st.dataframe(
        [
            {
                "Rank": i,
                "Candidate": r.candidate_name,
                "Email": r.candidate_email,
                "Score": r.final_score,
                "Gate": r.gate_status,
                "Recommendation": r.recommendation,
                "Evaluation": r.evaluation_number,
            }
            for i, r in enumerate(ordered, 1)
        ],
        width="stretch",
    )
