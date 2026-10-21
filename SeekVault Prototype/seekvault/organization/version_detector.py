import re
from typing import List, Dict, Any, Tuple
import numpy as np
from seekvault.database.repository import Repository
from seekvault.embeddings.manager import EmbeddingManager
from seekvault.config import VERSION_SIMILARITY_THRESHOLD
import logging

logger = logging.getLogger(__name__)

class VersionDetector:
    @staticmethod
    def extract_base_stem(filename: str) -> str:
        """Strip versioning suffixes like _v1, -v2, _draft, _final, (1) from filename."""
        # Remove extension
        stem = re.sub(r"\.[^.]+$", "", filename).strip()
        # Remove patterns like _v1, -v2, _draft, _final, _rev2, (1)
        base = re.sub(r"[-_.\s]+(?:v\d+|draft|final|rev\d+|copy|\(\d+\))", "", stem, flags=re.I)
        return base.strip().lower()

    @classmethod
    def detect_and_update_versions(
        cls,
        repository: Repository,
        similarity_threshold: float = VERSION_SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Detect near-duplicate document versions based on base stem alignment
        and high embedding cosine similarity.
        """
        files = repository.get_all_indexed_files(limit=1000, file_type="DOCUMENT")
        if len(files) < 2:
            return []

        # Filter out files without text content
        valid_files = []
        for f in files:
            content = repository.get_file_content(f["id"])
            if content and content.get("searchable_text_preview"):
                f["preview"] = content["searchable_text_preview"]
                valid_files.append(f)

        if len(valid_files) < 2:
            return []

        # Cluster by base stem
        stem_buckets: Dict[str, List[Dict[str, Any]]] = {}
        for f in valid_files:
            stem = cls.extract_base_stem(f["file_name"])
            if stem not in stem_buckets:
                stem_buckets[stem] = []
            stem_buckets[stem].append(f)

        embedder = EmbeddingManager.get_text_embedder()
        repository.clear_version_groups()

        detected_groups = []

        for stem, group_files in stem_buckets.items():
            # If multiple files share the base stem, verify semantic similarity
            if len(group_files) > 1:
                # Sort chronologically by modified_at
                sorted_files = sorted(group_files, key=lambda x: str(x.get("modified_at", "")))
                
                # Check pairwise similarity
                texts = [f["preview"] for f in sorted_files]
                vecs = embedder.embed_batch(texts)

                member_tuples: List[Tuple[int, float, int]] = []
                base_vec = vecs[0]
                member_tuples.append((sorted_files[0]["id"], 1.0, 1))

                for i in range(1, len(sorted_files)):
                    sim = float(np.dot(base_vec, vecs[i]))
                    if sim >= similarity_threshold:
                        member_tuples.append((sorted_files[i]["id"], round(sim, 4), i + 1))

                if len(member_tuples) > 1:
                    vg_id = repository.save_version_group(f"Versions of '{stem.capitalize()}'", member_tuples)
                    detected_groups.append({
                        "version_group_id": vg_id,
                        "group_name": f"Versions of '{stem.capitalize()}'",
                        "member_count": len(member_tuples)
                    })

        logger.info(f"Version detection completed. Found {len(detected_groups)} version groups.")
        return repository.get_all_version_groups()
