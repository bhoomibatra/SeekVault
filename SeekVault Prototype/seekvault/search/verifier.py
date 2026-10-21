import os
from pathlib import Path
from typing import List, Tuple, Dict, Any
from seekvault.database.repository import Repository
import logging

logger = logging.getLogger(__name__)

class AccessVerifier:
    @staticmethod
    def is_file_accessible(file_record: Dict[str, Any], repository: Repository) -> bool:
        """
        Verify at query-time that:
        1. File physical path exists on disk.
        2. File path is strictly located inside a currently active authorized folder.
        """
        if not file_record:
            return False

        file_path = file_record.get("file_path")
        if not file_path:
            return False

        # 1. Physical existence check
        if not os.path.exists(file_path):
            logger.info(f"Query-time suppression: File no longer exists on disk: {file_path}")
            return False

        # 2. Authorization boundary check
        if not repository.is_path_authorized(file_path):
            logger.info(f"Query-time suppression: Folder authorization revoked for path: {file_path}")
            return False

        return True

    @classmethod
    def filter_results(
        cls,
        candidate_results: List[Tuple[int, float]],
        repository: Repository
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Takes raw (file_id, score) FAISS tuples, resolves file records from SQLite,
        and applies zero-trust query-time authorization filtering.
        """
        verified_results = []
        for file_id, score in candidate_results:
            file_rec = repository.get_file_by_id(file_id)
            if not file_rec:
                continue

            if cls.is_file_accessible(file_rec, repository):
                verified_results.append((file_rec, score))

        return verified_results
