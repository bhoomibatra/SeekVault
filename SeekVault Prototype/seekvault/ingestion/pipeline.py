import os
from pathlib import Path
from typing import Dict, Any, Optional
import datetime
from seekvault.config import (
    DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS,
    TIER_FULL, TIER_REDACTED, TIER_METADATA_ONLY,
    TEXT_EMBEDDING_DIM, IMAGE_EMBEDDING_DIM
)
from seekvault.database.repository import Repository
from seekvault.extraction.text_extractor import TextExtractor
from seekvault.extraction.image_extractor import ImageExtractor
from seekvault.extraction.ocr_extractor import OCRExtractor
from seekvault.privacy.analyzer import PrivacyAnalyzer
from seekvault.privacy.sanitizer import PrivacySanitizer
from seekvault.privacy.classifier import PrivacyClassifier
from seekvault.embeddings.manager import EmbeddingManager
from seekvault.search.faiss_index import FaissIndex
from seekvault.search.engine import SearchEngine
from seekvault.organization.duplicate_detector import DuplicateDetector
from seekvault.organization.version_detector import VersionDetector
import logging

logger = logging.getLogger(__name__)

class IngestionPipeline:
    def __init__(self, repository: Optional[Repository] = None, search_engine: Optional[SearchEngine] = None):
        self.repository = repository or Repository()
        self.search_engine = search_engine or SearchEngine(repository=self.repository)

    def process_file(self, file_path_str: str, force_reembed: bool = False) -> Optional[Dict[str, Any]]:
        """
        Process a single file through the complete SeekVault pipeline:
        Authorization -> Extraction -> Privacy -> Classification -> Embedding -> Storage.
        Handles corrupt, locked, empty, and unsupported files gracefully with per-file status.
        """
        file_path = Path(file_path_str)
        if not file_path.exists() or not file_path.is_file():
            return None

        # 1. Authorization check
        if not self.repository.is_path_authorized(str(file_path)):
            logger.info(f"Skipping unauthorized file: {file_path}")
            return None

        folder_id = self.repository.get_folder_for_path(str(file_path))
        ext = file_path.suffix.lower()
        if ext not in (DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS):
            logger.debug(f"Skipping unsupported extension {ext}: {file_path}")
            return None

        # Handle locked or inaccessible files before stat/hash
        try:
            stat = file_path.stat()
            file_size = stat.st_size
            modified_at = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            file_hash = DuplicateDetector.calculate_file_hash(file_path)
        except (PermissionError, OSError) as e:
            logger.warning(f"File locked or inaccessible: {file_path} ({e})")
            file_id = self.repository.upsert_file(
                folder_id=folder_id,
                file_path=str(file_path),
                file_name=file_path.name,
                file_extension=ext,
                file_size=0,
                file_hash="",
                file_type="IMAGE" if ext in IMAGE_EXTENSIONS else "DOCUMENT",
                modified_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                status="FAILED",
                error_detail=f"Inaccessible or locked file: {e}"
            )
            return self.repository.get_file_by_id(file_id)

        is_image = ext in IMAGE_EXTENSIONS
        file_type = "IMAGE" if is_image else "DOCUMENT"

        # Check existing record to avoid redundant re-indexing if hash hasn't changed
        existing = self.repository.get_file_by_path(str(file_path))
        if not force_reembed and existing and existing.get("file_hash") == file_hash and existing.get("status") == "INDEXED":
            tier = existing.get("privacy_tier")
            file_id = existing["id"]
            # Integrity check: verify that vectors actually exist in FAISS index
            # (unless it's METADATA_ONLY or 0-byte file where no vectors should exist)
            vector_missing = False
            if tier != TIER_METADATA_ONLY and existing.get("file_size", 0) > 0:
                if is_image:
                    vector_missing = not self.search_engine.image_index.has_file(file_id)
                else:
                    vector_missing = not self.search_engine.text_index.has_file(file_id)

            if not vector_missing:
                logger.debug(f"File {file_path.name} unchanged (hash match and vector present). Skipping.")
                return existing
            else:
                logger.info(f"Integrity healing: file {file_path.name} (id={file_id}) indexed in DB but missing from FAISS. Regenerating embeddings.")

        logger.info(f"Ingesting {file_type}: {file_path.name}")

        # 2. Extraction & Privacy Processing
        if not is_image:
            extract_res = TextExtractor.extract(file_path)
            
            # If extraction failed (corrupt file, unreadable encoding, syntax error)
            if not extract_res.get("success", False):
                err_msg = extract_res.get("error") or "Unknown extraction failure"
                logger.warning(f"Extraction failed for {file_path.name}: {err_msg}")
                # Clean up any previous vectors if file became corrupted
                if existing:
                    self.search_engine.text_index.remove_file(existing["id"])
                file_id = self.repository.upsert_file(
                    folder_id=folder_id,
                    file_path=str(file_path),
                    file_name=file_path.name,
                    file_extension=ext,
                    file_size=file_size,
                    file_hash=file_hash,
                    file_type=file_type,
                    modified_at=modified_at,
                    privacy_tier=TIER_FULL,
                    status="FAILED",
                    error_detail=f"Extraction failed: {err_msg}"
                )
                return self.repository.get_file_by_id(file_id)

            raw_text = extract_res.get("text", "")
            raw_chars = len(raw_text)

            # Privacy Analysis
            detected_entities = PrivacyAnalyzer.analyze(raw_text) if raw_text else []
            privacy_tier = PrivacyClassifier.classify(file_path.name, raw_text, detected_entities)

            # Sanitization (original file is NEVER modified)
            if privacy_tier == TIER_REDACTED:
                sanitized_text = PrivacySanitizer.sanitize(raw_text, detected_entities)
            elif privacy_tier == TIER_METADATA_ONLY:
                sanitized_text = ""
            else:
                sanitized_text = raw_text

            # Save File record in SQLite
            file_id = self.repository.upsert_file(
                folder_id=folder_id,
                file_path=str(file_path),
                file_name=file_path.name,
                file_extension=ext,
                file_size=file_size,
                file_hash=file_hash,
                file_type=file_type,
                modified_at=modified_at,
                privacy_tier=privacy_tier,
                status="INDEXED",
                error_detail=None
            )

            # Save Content & Entities
            self.repository.save_file_content(
                file_id=file_id,
                raw_char_count=raw_chars,
                searchable_text_preview=raw_text[:2000],
                redacted_preview=sanitized_text[:2000],
                has_ocr=False
            )
            if detected_entities:
                self.repository.save_detected_entities(file_id, detected_entities)

            # 3. Vector Embedding with sliding-window chunking
            # Clean up any existing vector mappings for this file to prevent duplicates
            self.search_engine.text_index.remove_file(file_id)
            self.repository.clear_vector_mappings(file_id, "TEXT")
            if privacy_tier != TIER_METADATA_ONLY and sanitized_text.strip():
                embedder = EmbeddingManager.get_text_embedder()
                chunks = TextExtractor.chunk_text(sanitized_text, chunk_size=250, overlap=50)
                for chunk in chunks:
                    if chunk.strip():
                        vec = embedder.embed_text(chunk)
                        faiss_id = self.search_engine.text_index.add_vector(file_id, vec)
                        self.repository.save_vector_mapping(file_id, "TEXT", faiss_id, TEXT_EMBEDDING_DIM)

        else:
            # Image Processing
            meta_res = ImageExtractor.extract_metadata(file_path)
            if not meta_res.get("success", False):
                err_msg = meta_res.get("error") or "Failed to read image metadata"
                logger.warning(f"Image extraction failed for {file_path.name}: {err_msg}")
                if existing:
                    self.search_engine.image_index.remove_file(existing["id"])
                file_id = self.repository.upsert_file(
                    folder_id=folder_id,
                    file_path=str(file_path),
                    file_name=file_path.name,
                    file_extension=ext,
                    file_size=file_size,
                    file_hash=file_hash,
                    file_type=file_type,
                    modified_at=modified_at,
                    privacy_tier=TIER_FULL,
                    status="FAILED",
                    error_detail=f"Image error: {err_msg}"
                )
                return self.repository.get_file_by_id(file_id)

            visual_meta = {
                "width": meta_res.get("width"),
                "height": meta_res.get("height"),
                "color_mode": meta_res.get("color_mode"),
                "format": meta_res.get("format"),
                "aspect_ratio": meta_res.get("aspect_ratio"),
                "exif": meta_res.get("exif", {})
            }

            # Optional OCR on image (only if enabled and available)
            ocr_text = ""
            has_ocr = False
            from seekvault import config
            if getattr(config, "ENABLE_OCR", False) and OCRExtractor.is_available():
                ocr_res = OCRExtractor.extract_text(file_path)
                ocr_text = ocr_res.get("text", "")
                has_ocr = bool(ocr_text)

            detected_entities = []
            if ocr_text:
                detected_entities = PrivacyAnalyzer.analyze(ocr_text)

            privacy_tier = PrivacyClassifier.classify(file_path.name, ocr_text, detected_entities)

            # Save File record
            file_id = self.repository.upsert_file(
                folder_id=folder_id,
                file_path=str(file_path),
                file_name=file_path.name,
                file_extension=ext,
                file_size=file_size,
                file_hash=file_hash,
                file_type=file_type,
                modified_at=modified_at,
                privacy_tier=privacy_tier,
                status="INDEXED",
                visual_metadata=visual_meta,
                error_detail=None
            )

            self.repository.save_file_content(
                file_id=file_id,
                raw_char_count=len(ocr_text),
                searchable_text_preview=ocr_text[:2000],
                redacted_preview=ocr_text[:2000],
                has_ocr=has_ocr
            )
            if detected_entities:
                self.repository.save_detected_entities(file_id, detected_entities)

            # Multimodal Vision Vector Embedding
            self.search_engine.image_index.remove_file(file_id)
            self.repository.clear_vector_mappings(file_id, "IMAGE")
            if privacy_tier != TIER_METADATA_ONLY:
                try:
                    img_embedder = EmbeddingManager.get_image_embedder()
                    img_vec = img_embedder.embed_image(file_path)
                    faiss_id = self.search_engine.image_index.add_vector(file_id, img_vec)
                    self.repository.save_vector_mapping(file_id, "IMAGE", faiss_id, IMAGE_EMBEDDING_DIM)
                except Exception as e:
                    logger.warning(f"Image embedding failed for {file_path.name}: {e}")

        return self.repository.get_file_by_id(file_id)

    def remove_file(self, file_path_str: str) -> None:
        """Handle file deletion: prune from SQLite and vector indices."""
        file_rec = self.repository.get_file_by_path(file_path_str)
        if file_rec:
            file_id = file_rec["id"]
            if file_rec["file_type"] == "IMAGE":
                self.search_engine.image_index.remove_file(file_id)
            else:
                self.search_engine.text_index.remove_file(file_id)
            self.repository.delete_file_by_path(file_path_str)
            logger.info(f"Removed file from SeekVault: {file_path_str}")

    def scan_folder(self, folder_path: str, is_recursive: bool = True) -> int:
        """Scan and ingest all supported files within an authorized folder."""
        count = 0
        norm_dir = Path(folder_path)
        if not norm_dir.exists() or not norm_dir.is_dir():
            logger.warning(f"scan_folder: Directory does not exist: {folder_path}")
            return 0

        # Safety check: folder must be authorized
        if not self.repository.is_path_authorized(str(norm_dir)):
            logger.warning(f"scan_folder: Path is not authorized: {folder_path}")
            return 0

        pattern = "**/*" if is_recursive else "*"
        try:
            candidates = list(norm_dir.glob(pattern))
        except Exception as e:
            logger.error(f"Error enumerating directory {folder_path}: {e}")
            return 0

        for p in candidates:
            # Skip non-files
            if not p.is_file():
                continue
            
            # Skip temporary/lock files
            fname = p.name
            if (
                fname.startswith("~$")
                or fname.startswith(".~lock")
                or fname.endswith(".tmp")
                or fname.endswith(".crdownload")
                or fname.endswith(".part")
            ):
                continue

            if p.suffix.lower() in (DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS):
                try:
                    res = self.process_file(str(p))
                    if res and res.get("status") == "INDEXED":
                        count += 1
                except Exception as e:
                    logger.error(f"Error ingesting file {p}: {e}")

        # Update version clustering after scan
        VersionDetector.detect_and_update_versions(self.repository)
        return count

    def reconcile_missing_vectors(self) -> int:
        """
        Scan all SQLite file records marked as 'INDEXED'. If any non-METADATA_ONLY
        file is missing its embedding vectors in FAISS (e.g. index corruption, index deletion),
        regenerate and restore its embeddings automatically.

        Returns:
            Count of healed files.
        """
        healed_count = 0
        indexed_files = self.repository.get_all_files(status="INDEXED")
        for file_rec in indexed_files:
            tier = file_rec.get("privacy_tier")
            if tier == TIER_METADATA_ONLY:
                continue

            file_id = file_rec["id"]
            is_image = file_rec.get("file_type") == "IMAGE"
            vector_missing = False
            if is_image:
                vector_missing = not self.search_engine.image_index.has_file(file_id)
            else:
                vector_missing = not self.search_engine.text_index.has_file(file_id)

            if vector_missing:
                file_path_str = file_rec.get("file_path")
                if file_path_str and Path(file_path_str).exists():
                    logger.info(f"Reconciling vector for: {file_rec.get('file_name')} (id={file_id})")
                    res = self.process_file(file_path_str, force_reembed=True)
                    if res:
                        healed_count += 1
                else:
                    logger.warning(f"Cannot heal missing vector; file not found on disk: {file_path_str}")

        return healed_count

    def reconcile_startup(self) -> Dict[str, int]:
        """
        Synchronize SQLite database and FAISS vector indices on startup:
        1. Prune dead records from SQLite whose physical files no longer exist on disk
           or whose folders are no longer authorized.
        2. Remove corresponding orphaned vectors from FAISS text and image indices.
        3. Heal any missing vectors for existing indexed files.

        Returns:
            Dict containing counts: {"purged_records": int, "healed_vectors": int}
        """
        purged_ids = self.repository.prune_missing_files()
        for fid in purged_ids:
            self.search_engine.text_index.remove_file(fid)
            self.search_engine.image_index.remove_file(fid)

        healed_count = self.reconcile_missing_vectors()
        logger.info(
            f"Startup reconciliation complete: {len(purged_ids)} dead records purged, {healed_count} missing vectors healed."
        )
        return {
            "purged_records": len(purged_ids),
            "healed_vectors": healed_count
        }

