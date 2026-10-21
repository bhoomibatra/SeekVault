import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data_storage"
DATA_DIR.mkdir(exist_ok=True, parents=True)

DB_PATH = DATA_DIR / "seekvault.db"
INDEX_DIR = DATA_DIR / "indices"
INDEX_DIR.mkdir(exist_ok=True, parents=True)

TEXT_INDEX_PATH = INDEX_DIR / "text_index.faiss"
IMAGE_INDEX_PATH = INDEX_DIR / "image_index.faiss"
TEXT_METADATA_PATH = INDEX_DIR / "text_ids.json"
IMAGE_METADATA_PATH = INDEX_DIR / "image_ids.json"

# Supported File Formats
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALL_SUPPORTED_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS

# Machine Learning Models
TEXT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TEXT_EMBEDDING_DIM = 384

IMAGE_EMBEDDING_MODEL = "clip-ViT-B-32"
IMAGE_EMBEDDING_DIM = 512

# Privacy Classifications
TIER_FULL = "FULL"
TIER_REDACTED = "REDACTED"
TIER_METADATA_ONLY = "METADATA_ONLY"

# Sensitivity Entities
SENSITIVE_ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "PERSON",
    "AADHAAR_NUMBER",
    "PAN_NUMBER",
    "CREDIT_CARD",
    "CRYPTO",
    "US_SSN",
    "US_PASSPORT",
    "CONFIDENTIAL_KEY",
]

# High-sensitivity keywords that trigger METADATA_ONLY tier directly
METADATA_ONLY_KEYWORDS = {
    "password", "passphrase", "secret_key", "private_key",
    "recovery_seed", "master_key", "confidential_password",
    "api_secret", "bearer_token"
}

# Similarity Thresholds
VERSION_SIMILARITY_THRESHOLD = 0.82
SEARCH_DEFAULT_TOP_K = 10
SEARCH_MIN_SCORE = 0.20

# Watchdog Debounce Interval (seconds)
WATCHDOG_DEBOUNCE_SECONDS = 1.5
