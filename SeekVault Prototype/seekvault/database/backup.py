import os
import shutil
import zipfile
import datetime
import logging
from pathlib import Path
from typing import Tuple, Optional

from seekvault.config import DATA_DIR, DB_PATH, INDEX_DIR

logger = logging.getLogger(__name__)


def create_backup(destination_dir: Optional[Path] = None) -> Path:
    """Create a timestamped zip archive of SeekVault's SQLite database and FAISS vector indices.

    Does NOT include original source files (source files remain on disk in their original locations).
    Returns the Path to the generated zip archive.
    """
    dest = destination_dir or (DATA_DIR / "backups")
    dest.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = dest / f"seekvault_backup_{timestamp}.zip"

    with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        # 1. Add SQLite DB if it exists
        if DB_PATH.exists():
            zipf.write(DB_PATH, arcname="seekvault.db")

        # 2. Add FAISS indices and ID mappings
        if INDEX_DIR.exists():
            for child in INDEX_DIR.iterdir():
                if child.is_file():
                    zipf.write(child, arcname=f"indices/{child.name}")

    logger.info("Backup created at: %s", backup_file)
    return backup_file


def restore_backup(backup_zip: Path) -> Tuple[bool, str]:
    """Restore SQLite database and FAISS index files from a backup archive.

    Validates archive contents before extracting to prevent accidental file corruption.
    """
    if not backup_zip.exists():
        return False, f"Backup file does not exist: {backup_zip}"

    if not zipfile.is_zipfile(backup_zip):
        return False, f"File is not a valid zip archive: {backup_zip}"

    try:
        with zipfile.ZipFile(backup_zip, "r") as zipf:
            namelist = zipf.namelist()
            # Safety check: must contain seekvault.db
            if "seekvault.db" not in namelist:
                return False, "Invalid SeekVault backup: seekvault.db missing from archive root."

            # Extract directly into DATA_DIR
            zipf.extractall(DATA_DIR)

        logger.info("Restored backup from: %s", backup_zip)
        return True, "Backup successfully restored."
    except Exception as exc:
        logger.error("Failed to restore backup: %s", exc)
        return False, f"Restore failed: {exc}"
