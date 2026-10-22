import os
from typing import Optional
from seekvault.monitoring.folder_guard import FolderGuard
from seekvault.core.logger import logger

class AccessVerifier:
    """
    Query-Time Folder Authorization & Access Verifier.
    Re-verifies that candidate search result files:
    1. Still exist on disk (detects deleted files).
    2. Belong to an active user-authorized folder (detects un-authorized files / revoked folders).
    Prevents unauthorized files or stale deleted file records from appearing in search results.
    """

    @classmethod
    def is_file_accessible(cls, file_path: str, custom_db_path: Optional[str] = None) -> bool:
        if not file_path:
            return False
            
        try:
            norm_path = FolderGuard.normalize_path(file_path)
        except Exception:
            return False

        # 1. Verify file exists on disk
        if not os.path.exists(norm_path) or not os.path.isfile(norm_path):
            logger.debug(f"AccessVerifier: Rejected inaccessible file (deleted/moved): {norm_path}")
            return False

        # 2. Verify folder is currently authorized
        if not FolderGuard.is_path_authorized(norm_path, db_path=custom_db_path):
            logger.debug(f"AccessVerifier: Rejected unauthorized file path: {norm_path}")
            return False

        return True
