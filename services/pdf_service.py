from io import BytesIO
import logging

logger = logging.getLogger(__name__)


def extract_pdf_text(content: bytes) -> str:
    """Extract native PDF text. OCR fallback is handled by the caller."""
    try:
        import pdfplumber
        with pdfplumber.open(BytesIO(content)) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages).strip()
    except Exception:
        logger.exception("PDF text extraction failed")
        return ""
