from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ExifTags
import logging

logger = logging.getLogger(__name__)

class ImageExtractor:
    @staticmethod
    def extract_metadata(file_path: Path) -> Dict[str, Any]:
        """Extract visual metadata including dimensions, color mode, aspect ratio, and EXIF."""
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                mode = img.mode
                img_format = img.format
                aspect_ratio = round(width / height, 2) if height > 0 else 1.0

                exif_data = {}
                try:
                    raw_exif = img.getexif()
                    if raw_exif:
                        for tag_id, val in raw_exif.items():
                            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                            # Keep only basic scalar tags
                            if isinstance(val, (str, int, float)):
                                exif_data[tag_name] = val
                except Exception:
                    pass

                return {
                    "success": True,
                    "width": width,
                    "height": height,
                    "color_mode": mode,
                    "format": img_format,
                    "aspect_ratio": aspect_ratio,
                    "exif": exif_data,
                    "error": None
                }
        except Exception as e:
            logger.error(f"Error opening image {file_path}: {e}")
            return {
                "success": False,
                "width": 0,
                "height": 0,
                "color_mode": "UNKNOWN",
                "format": None,
                "aspect_ratio": 1.0,
                "exif": {},
                "error": str(e)
            }
