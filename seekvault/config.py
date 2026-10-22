import os
from pathlib import Path

# Application Metadata
APP_NAME = "SeekVault"
APP_VERSION = "0.1.0"

# User Data & Storage Paths
USER_HOME = Path.home()
SEEKVAULT_DIR = USER_HOME / ".seekvault"
SEEKVAULT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = os.environ.get("SEEKVAULT_DB_PATH", str(SEEKVAULT_DIR / "seekvault.db"))
INDEX_DIR = SEEKVAULT_DIR / "indices"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = SEEKVAULT_DIR / "seekvault.log"

# Supported Extensions for Initial Phase
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
SUPPORTED_EXTENSIONS = DOCUMENT_EXTENSIONS.union(IMAGE_EXTENSIONS)

# Scan Configuration
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB per file limit

# UI Aesthetics
THEME_PRIMARY = "#6366F1"
THEME_BACKGROUND = "#0F172A"
THEME_CARD_BG = "#1E293B"
