# Local AI Resume Screener

Local Streamlit resume evaluation application using Ollama.

Architecture:
- LLM: dynamic JD parsing, resume evidence extraction, evidence matching and contextual keyword analysis.
- Python: deterministic scoring, keyword arithmetic, gates, validation, ranking and persistence.
- SQLite: immutable evaluation snapshots and candidate history.

## Windows

    cd E:\ResumeScreener
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    ollama pull qwen3:8b
    streamlit run app.py

Tests:

    pytest -q

OCR requires Tesseract and Poppler to be installed separately on Windows.
