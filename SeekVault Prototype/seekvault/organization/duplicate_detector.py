import hashlib
from pathlib import Path
from typing import List, Dict, Any
from seekvault.database.repository import Repository

class DuplicateDetector:
    @staticmethod
    def calculate_file_hash(file_path: Path, block_size: int = 65536) -> str:
        """Compute SHA-256 hash of a file efficiently."""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(block_size), b""):
                sha.update(block)
        return sha.hexdigest()

    @classmethod
    def get_duplicates(cls, repository: Repository) -> List[Dict[str, Any]]:
        """Retrieve all duplicate clusters from the database."""
        return repository.get_duplicate_groups()
