import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
import pytesseract
import logging

logger = logging.getLogger(__name__)

# Search for common Windows Tesseract install locations
COMMON_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
]

class OCRExtractor:
    _is_available: Optional[bool] = None

    @classmethod
    def initialize(cls) -> bool:
        if cls._is_available is not None:
            return cls._is_available

        # Check if tesseract is on PATH
        if shutil.which("tesseract"):
            cls._is_available = True
            logger.info("Tesseract OCR found on system PATH.")
            return True

        # Check standard Windows paths
        for path in COMMON_TESSERACT_PATHS:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                cls._is_available = True
                logger.info(f"Tesseract OCR found at: {path}")
                return True

        cls._is_available = False
        logger.warning("Tesseract OCR binary not found. OCR extraction will operate in fallback mode.")
        return False

    @classmethod
    def is_available(cls) -> bool:
        if cls._is_available is None:
            cls.initialize()
        return bool(cls._is_available)

    @classmethod
    def extract_text(cls, image_path: Path) -> Dict[str, Any]:
        """Extract text from image using Tesseract OCR, with graceful fallback."""
        if not cls.is_available():
            return {
                "success": False,
                "text": "",
                "available": False,
                "error": "Tesseract OCR binary is not installed or not in PATH."
            }

        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")
                text = pytesseract.image_to_string(img)
                return {
                    "success": True,
                    "text": text.strip(),
                    "available": True,
                    "error": None
                }
        except Exception as e:
            logger.warning(f"OCR extraction failed for {image_path}: {e}")
            return {
                "success": False,
                "text": "",
                "available": True,
                "error": str(e)
            }
