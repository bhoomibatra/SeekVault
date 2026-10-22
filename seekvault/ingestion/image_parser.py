import os
from PIL import Image, ImageOps
import pytesseract
from typing import Dict, Any, Optional
from seekvault.ingestion.models import ExtractionResult
from seekvault.core.logger import logger

def extract_image(file_path: str) -> ExtractionResult:
    """
    Extracts image metadata via Pillow and text via Tesseract OCR when available.
    Does not alter or write to the original image file.
    """
    norm_path = os.path.abspath(os.path.realpath(file_path))
    if not os.path.exists(norm_path):
        return ExtractionResult(
            file_path=norm_path,
            file_type="image",
            extracted_text="",
            metadata={},
            extraction_method="pillow_metadata",
            extraction_status="FAILED",
            error_message="File not found."
        )

    try:
        with Image.open(norm_path) as img:
            # Correct orientation if EXIF orientation tag exists
            img = ImageOps.exif_transpose(img)
            
            width, height = img.size
            img_format = img.format or os.path.splitext(norm_path)[1].lstrip(".").upper()
            mode = img.mode
            channels = len(img.getbands()) if hasattr(img, "getbands") else 1
            
            image_metadata = {
                "width": width,
                "height": height,
                "format": img_format,
                "color_mode": mode,
                "channels": channels,
                "aspect_ratio": round(width / max(height, 1), 2)
            }
            
            # Attempt Tesseract OCR extraction
            ocr_text = ""
            ocr_status = "SUCCESS"
            extraction_method = "tesseract_ocr"
            error_msg = None
            
            try:
                # Convert image to RGB for Tesseract OCR stability
                if img.mode != "RGB":
                    rgb_img = img.convert("RGB")
                else:
                    rgb_img = img
                    
                raw_ocr = pytesseract.image_to_string(rgb_img)
                ocr_text = raw_ocr.strip() if raw_ocr else ""
                image_metadata["ocr_available"] = True
                image_metadata["ocr_char_count"] = len(ocr_text)
                
                if not ocr_text:
                    ocr_status = "EMPTY"
                    
            except (pytesseract.TesseractNotFoundError, FileNotFoundError):
                logger.warning(f"Tesseract OCR binary not found on system PATH for '{norm_path}'. Extracting image metadata only.")
                extraction_method = "pillow_metadata"
                image_metadata["ocr_available"] = False
                image_metadata["ocr_char_count"] = 0
                error_msg = "Tesseract OCR binary not installed or not found on system PATH."
            except Exception as ocr_err:
                logger.warning(f"Tesseract OCR failed for '{norm_path}': {ocr_err}")
                extraction_method = "pillow_metadata"
                image_metadata["ocr_available"] = False
                image_metadata["ocr_char_count"] = 0
                error_msg = f"OCR engine error: {ocr_err}"

            return ExtractionResult(
                file_path=norm_path,
                file_type="image",
                extracted_text=ocr_text,
                metadata=image_metadata,
                extraction_method=extraction_method,
                extraction_status=ocr_status,
                error_message=error_msg
            )

    except Exception as e:
        logger.error(f"Image extraction failed for '{norm_path}': {e}")
        return ExtractionResult(
            file_path=norm_path,
            file_type="image",
            extracted_text="",
            metadata={},
            extraction_method="pillow_metadata",
            extraction_status="FAILED",
            error_message=str(e)
        )
