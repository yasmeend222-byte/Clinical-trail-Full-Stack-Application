"""Text extraction from uploaded trial protocol documents."""
import io

from fastapi import HTTPException
from pypdf import PdfReader

MAX_BYTES = 15 * 1024 * 1024


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 15 MB)")
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise HTTPException(400, f"Could not read PDF: {exc}") from exc
    if name.endswith((".txt", ".md", ".text")):
        return data.decode("utf-8", errors="replace")
    raise HTTPException(400, "Unsupported file type. Upload a .pdf or .txt protocol.")
