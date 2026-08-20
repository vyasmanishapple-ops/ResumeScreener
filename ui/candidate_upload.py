import tempfile
from pathlib import Path
import streamlit as st
from services.document_parser import extract_text
from services.ocr_service import ocr_if_needed

def upload_candidates():
    files = st.file_uploader(
        "Candidate resumes",
        type=["pdf", "docx"],
        accept_multiple_files=True,
    )
    outputs = []
    for uploaded in files or []:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=Path(uploaded.name).suffix,
        ) as tmp:
            tmp.write(uploaded.getbuffer())
            path = tmp.name
        text, pages, quality_ok = extract_text(path)
        ocr_used = False
        if not quality_ok:
            improved = ocr_if_needed(path, text)
            ocr_used = improved != text
            text = improved
        outputs.append({
            "filename": uploaded.name,
            "text": text,
            "pages": pages,
            "quality_ok": quality_ok,
            "ocr_used": ocr_used,
        })
    return outputs
