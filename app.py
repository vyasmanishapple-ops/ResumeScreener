
from pathlib import Path
import yaml
import streamlit as st

from database.database import init_db
from database.repositories import (
    get_evaluation,
    save_evaluation,
    save_jd_version,
)
from models.evaluation import EvaluationResult
from services.jd_parser import parse_jd
from services.resume_parser import parse_resume
from services.evaluation_service import evaluate_candidate
from ui.job_setup import keyword_editor
from ui.candidate_upload import upload_candidates
from ui.evaluation import render_evaluation
from ui.history import render_history
from ui.ranking import render_ranking
from ui.jd_review import render_jd_review


st.set_page_config(
    page_title="Local AI Resume Screener",
    layout="wide",
)

init_db()


evaluation_number = st.query_params.get("evaluation")

if evaluation_number:
    payload = get_evaluation(evaluation_number)

    if payload:
        result = EvaluationResult.model_validate(payload)

        if st.button("← Back"):
            st.query_params.clear()
            st.rerun()

        st.caption(
            "Historical evaluation — loaded from SQLite; "
            "LLM was not rerun."
        )

        render_evaluation(
            result,
            editable=True,
        )
        st.stop()

    st.error("Evaluation not found.")
    st.query_params.clear()


st.title("Local AI Resume Screener")


page = st.sidebar.radio(
    "Page",
    [
        "New Evaluation",
        "Candidate History",
    ],
)


if page == "Candidate History":
    render_history()
    st.stop()


models = yaml.safe_load(
    Path("config/models.yaml").read_text(
        encoding="utf-8"
    )
)

selected_model = st.sidebar.selectbox(
    "Ollama Model",
    models["models"],
)


left, right = st.columns([3, 2], gap="large")

with left:
    job_title_override = st.text_input(
        "Job Title Override (optional)"
    )
    jd_text = st.text_area(
        "Job Description",
        height=430,
        placeholder="Paste the complete job description here...",
    )

with right:
    signals = keyword_editor()


analyze_requested = st.button(
    "Analyze Job Description",
    type="primary",
)

if analyze_requested:
    has_unsaved = bool(st.session_state.get("jd") and st.session_state.get("jd_dirty"))
    if has_unsaved:
        st.warning("You have unsaved recruiter changes. Re-analyzing will replace the current review.")
        st.session_state["confirm_reanalyze"] = True
    elif not jd_text.strip():
        st.error("Enter a Job Description.")
    else:
        st.session_state["confirm_reanalyze"] = False

if st.session_state.get("confirm_reanalyze"):
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Yes, discard and re-analyze", type="primary"):
            st.session_state["confirm_reanalyze"] = False
            if not jd_text.strip():
                st.error("Enter a Job Description.")
            else:
                with st.spinner("Dynamically analyzing JD..."):
                    try:
                        analysis = parse_jd(jd_text, selected_model)
                        if job_title_override.strip():
                            analysis.job_title = job_title_override.strip()
                        st.session_state["jd"] = analysis
                        st.session_state["jd_ai_original"] = analysis.model_copy(deep=True)
                        st.session_state["jd_text"] = jd_text
                        st.session_state["jd_dirty"] = False
                        st.session_state["jd_version_id"] = None
                        st.success("JD analysis completed.")
                    except Exception as error:
                        st.error(f"JD analysis failed: {error}")
    with c2:
        if st.button("Cancel"):
            st.session_state["confirm_reanalyze"] = False
            st.rerun()
elif analyze_requested and jd_text.strip() and not st.session_state.get("jd_dirty"):
    with st.spinner("Dynamically analyzing JD..."):
        try:
            analysis = parse_jd(jd_text, selected_model)
            if job_title_override.strip():
                analysis.job_title = job_title_override.strip()
            st.session_state["jd"] = analysis
            st.session_state["jd_ai_original"] = analysis.model_copy(deep=True)
            st.session_state["jd_text"] = jd_text
            st.session_state["jd_dirty"] = False
            st.session_state["jd_version_id"] = None
            st.success("JD analysis completed.")
        except Exception as error:
            st.error(f"JD analysis failed: {error}")


if "jd" in st.session_state:

    st.session_state["jd"] = render_jd_review(st.session_state["jd"])

    if st.session_state.get("jd_approved_pending_save"):
        try:
            version_id = save_jd_version(
                st.session_state["jd"],
                st.session_state.get("jd_text", ""),
                st.session_state.get("jd_ai_original", st.session_state["jd"]),
            )
            st.session_state["jd_version_id"] = version_id
            st.session_state["jd_approved_pending_save"] = False
            st.session_state["jd_dirty"] = False
            st.success(f"JD model saved as version {version_id}.")
        except Exception as error:
            st.error(f"Unable to save the approved JD model: {error}")

    st.divider()

    uploaded = upload_candidates()

    if uploaded and st.button(
        "Evaluate Candidates",
        type="primary",
    ):
        results = []

        for item in uploaded:
            filename = item["filename"]
            text = item["text"]

            with st.spinner(
                f"Evaluating {filename}..."
            ):
                try:
                    if len(text.strip()) < 100:
                        st.warning(
                            f"{filename}: insufficient "
                            "readable text; skipped."
                        )
                        continue

                    if item["ocr_used"]:
                        st.info(
                            f"{filename}: OCR was used."
                        )

                    candidate = parse_resume(
                        text,
                        selected_model,
                    )

                    result = evaluate_candidate(
                        st.session_state["jd"],
                        candidate,
                        text,
                        signals,
                        selected_model,
                    )

                    result = save_evaluation(
                        result,
                        st.session_state["jd_text"],
                    )

                    results.append(result)

                except Exception as error:
                    st.error(
                        f"{filename}: "
                        f"evaluation failed: {error}"
                    )

        st.session_state["results"] = results


if st.session_state.get("results"):
    render_ranking(
        st.session_state["results"]
    )

    for result in st.session_state["results"]:
        with st.expander(
            f"{result.evaluation_number} — "
            f"{result.candidate_name} — "
            f"{result.final_score:.1f}/100"
        ):
            render_evaluation(result)
