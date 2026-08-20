import streamlit as st
import pdfplumber
import docx

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List

# ==========================================
# 1. DEFINE DATA PATTERNS FOR DATA EXTRACTION
# ==========================================
class SkillEvaluation(BaseModel):
    skill_name: str = Field(description="The specific key skill, tool, framework, or experience threshold explicitly required by the JD")
    score: int = Field(description="Strict score out of 10 based on clear evidence of application in the candidate's resume history")
    justification: str = Field(description="Concise sentence detailing exactly why this rating was given based on resume evidence")

class CandidateEvaluation(BaseModel):
    candidate_name: str = Field(description="Full extracted name of the applicant")
    skills_assessment: List[SkillEvaluation] = Field(description="Comprehensive list mapping all key core competencies identified in the JD")
    final_score: int = Field(description="Overall mathematically balanced alignment score out of 100 for this applicant")

# ==========================================
# 2. FILE PROCESSING UTILITIES
# ==========================================
def extract_text(file) -> str:
    text = ""
    file_type = file.name.split('.')[-1].lower()
    if file_type == "pdf":
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    elif file_type in ["docx", "doc"]:
        doc = docx.Document(file)
        text = "\n".join([para.text for para in doc.paragraphs])
    return text

# ==========================================
# 3. CHAT ENGINE WITH LLM PARAMS & PROMPTS
# ==========================================
def evaluate_candidate(resume_text: str, job_description: str, model_name: str, positive_prompt: str, negative_prompt: str) -> CandidateEvaluation:
    # Uses the correct, non-crashing wrapper layer to integrate with local Ollama service
    client = instructor.from_openai(
        OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",  # Required placeholder initialization token
        ),
        mode=instructor.Mode.JSON,
    )
    
    # Injected the custom positive and negative system behaviors into the core engine prompt
    prompt = f"""
    You are an objective, precise executive recruiter. 
    Analyze the provided Job Description to extract critical technical requirements, platform tools, and leadership thresholds.
    Cross-reference these extracted metrics against the Candidate Resume. 
    Be conservative and strict with scoring—do not assume experience that is not explicitly stated.
    
    CRITICAL EVALUATION FOCUS (POSITIVE INSTRUCTIONS):
    {positive_prompt if positive_prompt.strip() else "Evaluate based strictly on explicit alignment with the JD."}
    
    WHAT TO PENALIZE/IGNORE (NEGATIVE INSTRUCTIONS):
    {negative_prompt if negative_prompt.strip() else "Do not award points for vague mentions, generic buzzwords, or unrelated skills."}
    
    JOB DESCRIPTION:
    {job_description}
    
    CANDIDATE RESUME:
    {resume_text}
    """
    
    return client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a professional recruiting auditor. Provide completely unbiased, structured assessments based strictly on text evidence and evaluation criteria."},
            {"role": "user", "content": prompt}
        ],
        response_model=CandidateEvaluation,
        extra_body={
            "options": {
                "temperature": 0.0,       # Eliminates AI creativity; ensures completely deterministic outcomes
                "num_ctx": 8192,          # Protects system memory from truncating longer resumes or enterprise JDs
                "top_p": 0.9              # Enhances token predictability filters
            }
        }
    )

# ==========================================
# 4. COMPREHENSIVE USER INTERFACE LAYOUT
# ==========================================
st.set_page_config(page_title="Local AI Resume Screener", layout="wide")
st.title("🎯 Local AI Resume Evaluator & Screener")
st.markdown("### Tailored Candidate Auditing powered by Private Local Intelligence Models")

st.sidebar.header("System Configuration")

# Verified local engine model list inventory
selected_model = st.sidebar.selectbox(
    "Select Local Ollama Engine",
    ["qwen2.5-coder:32b", "qwen3-coder:30b", "llama3.2-vision:11b"],
    index=0
)

st.sidebar.divider()
st.sidebar.header("Model Tuning Prompts")

# --- ADDED POSITIVE AND NEGATIVE PROMPT INPUTS TO SIDEBAR ---
pos_prompt = st.sidebar.text_area(
    "🟢 Positive Prompt (What to emphasize)", 
    height=100, 
    placeholder="e.g., Look heavily for hands-on production cloud architecture and senior engineering mentorship experience."
)

neg_prompt = st.sidebar.text_area(
    "🔴 Negative Prompt (What to penalize/ignore)", 
    height=100, 
    placeholder="e.g., Ignore generic technical summaries, buzzword-stuffed profiles, or boot camps without practical production application."
)

st.sidebar.divider()
st.sidebar.info(
    "💡 **Screening Logic Note:**\n"
    "System temperature is locked at **0.0** inside the execution layer to maintain rigid grading fairness across all candidate profiles."
)

job_desc = st.text_area("📋 Paste Target Job Description (JD) Here", height=220, placeholder="Enter roles, skills, and target engineering criteria...")
uploaded_files = st.file_uploader("📂 Drop Candidate Resumes Here", type=["pdf", "docx"], accept_multiple_files=True)

if st.button("🚀 Execute Candidate Evaluations", type="primary"):
    if not job_desc.strip() or not uploaded_files:
        st.error("Missing Input Parameters: Please provide a target job description and attach at least one candidate resume file.")
    else:
        st.divider()
        st.subheader("📊 Candidate Audit Reports")
        
        for uploaded_file in uploaded_files:
            with st.spinner(f"Auditing file pipeline: {uploaded_file.name}..."):
                try:
                    resume_text = extract_text(uploaded_file)
                    if not resume_text.strip():
                        st.warning(f"Skipping empty or unreadable file asset: {uploaded_file.name}")
                        continue
                    
                    # Execute processing block including prompt arguments
                    result = evaluate_candidate(resume_text, job_desc, selected_model, pos_prompt, neg_prompt)
                    
                    # Build structured presentation metric wrappers
                    with st.expander(f"👤 Candidate: {result.candidate_name} — Composite Score: {result.final_score}/100", expanded=True):
                        col1, col2 = st.columns([1, 3]) # Fixed parameter mapping layout
                        
                        with col1:
                            st.metric(label="Overall Alignment", value=f"{result.final_score} / 100")
                        
                        with col2:
                            st.markdown(f"#### **Applicant Name:** {result.candidate_name}")
                            st.markdown(f"**Source Document Reference:** `{uploaded_file.name}`")
                        
                        st.markdown("---")
                        st.markdown("#### **Target Matrix Breakdown:**")
                        
                        # Generate data grid metrics cleanly
                        for item in result.skills_assessment:
                            if item.score >= 8:
                                badge = "🟢 Strong Match"
                            elif item.score >= 5:
                                badge = "🟡 Moderate Match"
                            else:
                                badge = "🔴 Low Match"
                                
                            st.markdown(f"##### **{item.skill_name}** | {badge} (`{item.score}/10`)")
                            st.markdown(f"*Auditor Notes:* {item.justification}")
                            st.markdown("")
                            
                except Exception as e:
                    st.error(f"Error auditing {uploaded_file.name}: {str(e)}")
