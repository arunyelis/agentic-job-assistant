import io
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader


MAX_RESUME_BYTES = 5 * 1024 * 1024
MAX_RESUME_CHARS = 30_000
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


class ResumeError(ValueError):
    pass


def _clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:MAX_RESUME_CHARS]


def extract_resume(file_name: str, data: bytes) -> str:
    extension = Path(file_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ResumeError("Use a PDF, DOCX, TXT, or Markdown resume.")
    if not data:
        raise ResumeError("The uploaded resume is empty.")
    if len(data) > MAX_RESUME_BYTES:
        raise ResumeError("The resume must be 5 MB or smaller.")

    try:
        if extension == ".pdf":
            if not data.startswith(b"%PDF"):
                raise ResumeError("That file does not appear to be a valid PDF.")
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif extension == ".docx":
            if not data.startswith(b"PK"):
                raise ResumeError("That file does not appear to be a valid DOCX file.")
            document = Document(io.BytesIO(data))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        else:
            text = data.decode("utf-8-sig")
    except ResumeError:
        raise
    except Exception as error:
        raise ResumeError("The resume could not be read. Try exporting it again.") from error

    text = _clean_text(text)
    if len(text) < 40:
        raise ResumeError("The resume did not contain enough readable text.")
    return text
