import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    logger.warning("pytesseract or pdf2image not installed. OCR fallback disabled.")

def perform_ocr_on_pdf(file_path: str) -> Optional[str]:
    """
    Fallback method to extract text from scanned PDFs using OCR.
    """
    if not HAS_OCR:
        logger.error("OCR dependencies missing. Cannot process scanned PDF.")
        return None
        
    try:
        logger.info(f"Starting OCR fallback for: {file_path}")
        pages = convert_from_path(file_path, 300)
        
        extracted_text = []
        for i, page in enumerate(pages):
            text = pytesseract.image_to_string(page)
            extracted_text.append(f"--- PAGE {i+1} ---\n{text}")
            
        full_text = "\n\n".join(extracted_text)
        logger.info("OCR completed successfully.")
        return full_text
    except Exception as e:
        logger.error(f"OCR processing failed for {file_path}: {e}")
        return None
