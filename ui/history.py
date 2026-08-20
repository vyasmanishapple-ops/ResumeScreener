import streamlit as st
from database.repositories import history_by_email

def render_history():
    st.title("Candidate History")
    email = st.text_input("Candidate email address")
    if st.button("Search History"):
        rows = history_by_email(email)
        if not rows:
            st.info("No evaluations found.")
            return

        for row in rows:
            label = (
                f"{row.evaluation_number} : "
                f"{row.job_title} : "
                f"{row.final_score:.1f} - "
                f"{row.created_at.strftime('%d %b %Y')}"
            )
            # Actual clickable URL; opening it loads the stored record.
            st.markdown(
                f"[{label}](?evaluation={row.evaluation_number})"
            )
