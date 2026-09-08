from io import BytesIO
import logging

logger = logging.getLogger(__name__)


def extract_scanned_pdf_text(content: bytes) -> str:
    """OCR each PDF page with easyocr when native text extraction is empty."""
    try:
        import fitz
        import easyocr
        from PIL import Image
        import numpy as np
        reader = easyocr.Reader(["en"], gpu=False)
        document = fitz.open(stream=content, filetype="pdf")
        parts = []
        for page in document:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.open(BytesIO(pixmap.tobytes("png")))
            parts.append("\n".join(reader.readtext(np.array(image), detail=0, paragraph=True)))
        return "\n".join(parts).strip()
    except Exception:
        logger.exception("OCR extraction failed")
        return ""
