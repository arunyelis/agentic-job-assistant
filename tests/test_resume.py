import io

import pytest
from docx import Document

from backend.resume import ResumeError, extract_resume


RESUME_TEXT = (
    "Alex Morgan\nAI Engineer\nBuilt Python services and evaluated language model workflows."
)


def test_extract_text_resume():
    assert "AI Engineer" in extract_resume("resume.txt", RESUME_TEXT.encode())


def test_extract_docx_resume():
    document = Document()
    document.add_paragraph(RESUME_TEXT)
    output = io.BytesIO()
    document.save(output)

    assert "language model workflows" in extract_resume("resume.docx", output.getvalue())


def test_reject_unsupported_resume():
    with pytest.raises(ResumeError, match="PDF, DOCX, TXT, or Markdown"):
        extract_resume("resume.rtf", RESUME_TEXT.encode())
