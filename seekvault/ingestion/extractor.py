import os
from seekvault.config import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS
from seekvault.ingestion.models import ExtractionResult
from seekvault.ingestion.document_parser import extract_pdf, extract_docx, extract_txt
from seekvault.ingestion.image_parser import extract_image
from seekvault.core.logger import logger

def extract_file(file_path: str) -> ExtractionResult:
    """
    Unified local file extractor.
    Dispatches to appropriate parser based on extension:
    - PDF: PyMuPDF
    - DOCX: python-docx
    - TXT: Standard Python file reader
    - Image (PNG, JPG, JPEG): Pillow & Tesseract OCR
    """
    norm_path = os.path.abspath(os.path.realpath(file_path))
    if not os.path.exists(norm_path):
        return ExtractionResult(
            file_path=norm_path,
            file_type="unknown",
            extracted_text="",
            metadata={},
            extraction_method="none",
            extraction_status="FAILED",
            error_message=f"File not found: {norm_path}"
        )

    ext = os.path.splitext(norm_path)[1].lower()
    
    if ext == ".pdf":
        return extract_pdf(norm_path)
    elif ext == ".docx":
        return extract_docx(norm_path)
    elif ext in [".txt", ".md"]:
        return extract_txt(norm_path)
    elif ext in IMAGE_EXTENSIONS:
        return extract_image(norm_path)
    else:
        logger.warning(f"Unified Extractor: Unsupported file extension '{ext}' for file '{norm_path}'.")
        return ExtractionResult(
            file_path=norm_path,
            file_type="unknown",
            extracted_text="",
            metadata={"extension": ext},
            extraction_method="none",
            extraction_status="FAILED",
            error_message=f"Unsupported file format: '{ext}'"
        )
