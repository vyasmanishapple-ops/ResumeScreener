from pathlib import Path
import pdfplumber
from docx import Document

def extract_text(file_path):
    extension = Path(file_path).suffix.lower()
    if extension == ".pdf":
        chunks = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                chunks.append(page.extract_text() or "")
        text = "\n".join(chunks)
        pages = len(chunks)
    elif extension == ".docx":
        document = Document(file_path)
        text = "\n".join(p.text for p in document.paragraphs)
        pages = 1
    else:
        raise ValueError(f"Unsupported file type: {extension}")
    return text, pages, len(text.strip()) >= 100
