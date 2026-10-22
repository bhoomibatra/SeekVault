from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class ExtractionResult:
    """
    Unified extraction result data structure across all supported file types.
    """
    file_path: str
    file_type: str                   # "document" or "image"
    extracted_text: str              # Extracted text content
    metadata: Dict[str, Any]         # Extracted metadata (pages, dimensions, char count, etc.)
    extraction_method: str           # e.g., "pymupdf", "python-docx", "text_reader", "tesseract_ocr", "pillow_metadata"
    extraction_status: str           # "SUCCESS", "PARTIAL", "FAILED", "EMPTY"
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_type": self.file_type,
            "extracted_text": self.extracted_text,
            "metadata": self.metadata,
            "extraction_method": self.extraction_method,
            "extraction_status": self.extraction_status,
            "error_message": self.error_message,
        }
