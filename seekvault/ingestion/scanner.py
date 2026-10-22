import os
import mimetypes
from datetime import datetime
from typing import Dict, Any, List, Optional

from seekvault.config import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS, SUPPORTED_EXTENSIONS, MAX_FILE_SIZE_BYTES
from seekvault.core.database import upsert_file_metadata, get_authorized_folders, get_db_connection
from seekvault.core.logger import logger
from seekvault.ingestion.hasher import compute_sha256
from seekvault.monitoring.folder_guard import FolderGuard
from seekvault.ingestion.extractor import extract_file
from seekvault.privacy.classifier import PrivacyClassifier
from seekvault.ingestion.chunker import TextChunker
from seekvault.embeddings.text_embedder import TextEmbedder
from seekvault.embeddings.faiss_manager import FAISSManager

class FolderScanner:
    """
    Incremental Folder Scanner & Privacy Vector Indexer.
    Detects supported files, skips unchanged files based on SHA-256 hashes,
    embeds privacy-approved text representations, and updates FAISS + SQLite.
    """

    @staticmethod
    def classify_file_type(extension: str) -> str:
        ext = extension.lower()
        if ext in DOCUMENT_EXTENSIONS:
            return "document"
        elif ext in IMAGE_EXTENSIONS:
            return "image"
        return "other"

    @classmethod
    def scan_file(cls, file_path: str, custom_db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        norm_path = FolderGuard.normalize_path(file_path)
        
        if not FolderGuard.is_path_authorized(norm_path, db_path=custom_db_path):
            logger.warning(f"Scanner: Rejected unauthorized file path: {norm_path}")
            return None
            
        if not os.path.exists(norm_path):
            return None
            
        ext = os.path.splitext(norm_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return None
            
        try:
            stat = os.stat(norm_path)
            file_size = stat.st_size
            
            if file_size > MAX_FILE_SIZE_BYTES:
                logger.warning(f"Scanner: Skipping oversized file ({file_size} bytes): {norm_path}")
                return None
                
            file_name = os.path.basename(norm_path)
            created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
            modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            sha256_hash = compute_sha256(norm_path)
            file_type = cls.classify_file_type(ext)

            # INCREMENTAL INDEXING CHECK: Check if file is unchanged in SQLite
            conn = get_db_connection(custom_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, sha256_hash, indexing_status, privacy_tier FROM files WHERE file_path = ?",
                (norm_path,)
            )
            existing = cursor.fetchone()
            conn.close()

            if existing and existing["sha256_hash"] == sha256_hash and existing["indexing_status"] == "INDEXED":
                logger.info(f"Scanner: Incremental skip unchanged file: {norm_path}")
                return {
                    "id": existing["id"],
                    "file_path": norm_path,
                    "file_name": file_name,
                    "indexing_status": "SKIPPED",
                    "privacy_tier": existing["privacy_tier"]
                }
            
            # Phase 2: Perform text & metadata extraction
            extraction_result = extract_file(norm_path)
            
            # Phase 3: Run Privacy Classification (FULL, REDACTED, METADATA_ONLY)
            classifier = PrivacyClassifier()
            classification = classifier.classify(extraction_result.extracted_text)
            
            stored_text = classification.redacted_text if classification.tier != "METADATA_ONLY" else ""
            
            # Clear old vector mappings if re-indexing a modified file
            if existing:
                cls._clear_file_vectors(existing["id"], custom_db_path=custom_db_path)

            file_record = {
                "file_path": norm_path,
                "file_name": file_name,
                "file_extension": ext,
                "file_size": file_size,
                "mime_type": mimetypes.guess_type(norm_path)[0] or "application/octet-stream",
                "created_at": created_at,
                "modified_at": modified_at,
                "sha256_hash": sha256_hash,
                "phash": None,
                "file_type": file_type,
                "privacy_tier": classification.tier,
                "indexing_status": "INDEXED",
                "error_message": extraction_result.error_message,
                "extracted_text": stored_text,
                "extraction_method": extraction_result.extraction_method,
                "extraction_status": extraction_result.extraction_status
            }
            
            file_id = upsert_file_metadata(file_record, custom_db_path=custom_db_path)
            file_record["id"] = file_id
            
            # Phase 4: Vector Generation & FAISS Store Sync for FULL and REDACTED tiers
            if classification.tier != "METADATA_ONLY" and stored_text.strip():
                cls._index_file_chunks(
                    file_id=file_id,
                    file_path=norm_path,
                    text=stored_text,
                    custom_db_path=custom_db_path
                )
                
            return file_record
            
        except Exception as e:
            logger.error(f"Scanner: Error scanning file '{norm_path}': {e}")
            return None

    @classmethod
    def _clear_file_vectors(cls, file_id: int, custom_db_path: Optional[str] = None) -> None:
        conn = get_db_connection(custom_db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT faiss_vector_id FROM faiss_index_mapping WHERE file_id = ?", (file_id,))
            rows = cursor.fetchall()
            old_faiss_ids = [r["faiss_vector_id"] for r in rows if r["faiss_vector_id"] is not None]
            
            if old_faiss_ids:
                faiss_mgr = FAISSManager()
                faiss_mgr.remove_vectors(old_faiss_ids)
                
            cursor.execute("DELETE FROM document_chunks WHERE file_id = ?", (file_id,))
            cursor.execute("DELETE FROM faiss_index_mapping WHERE file_id = ?", (file_id,))
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def _index_file_chunks(
        cls,
        file_id: int,
        file_path: str,
        text: str,
        custom_db_path: Optional[str] = None
    ) -> None:
        chunker = TextChunker()
        chunks = chunker.chunk_text(text)
        if not chunks:
            return

        embedder = TextEmbedder()
        faiss_mgr = FAISSManager()
        
        passages = [c.text for c in chunks]
        vectors = embedder.encode_passages(passages)
        
        conn = get_db_connection(custom_db_path)
        cursor = conn.cursor()
        
        allocated_faiss_ids = []
        
        try:
            for i, chunk in enumerate(chunks):
                cursor.execute(
                    """
                    INSERT INTO document_chunks (file_id, chunk_index, page_number, start_char_idx, end_char_idx, raw_text, redacted_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (file_id, chunk.chunk_index, chunk.page_number, chunk.start_char_idx, chunk.end_char_idx, chunk.text, chunk.text)
                )
                chunk_db_id = cursor.lastrowid
                
                cursor.execute(
                    """
                    INSERT INTO faiss_index_mapping (index_type, entity_type, entity_id, file_id)
                    VALUES ('text', 'document_chunk', ?, ?)
                    """,
                    (chunk_db_id, file_id)
                )
                faiss_vector_id = cursor.lastrowid
                allocated_faiss_ids.append(faiss_vector_id)
                
                cursor.execute(
                    "UPDATE document_chunks SET vector_faiss_id = ? WHERE id = ?",
                    (faiss_vector_id, chunk_db_id)
                )

            conn.commit()
            
            # Insert vectors with allocated integer IDs into FAISS
            faiss_mgr.add_vectors(vectors, allocated_faiss_ids)
            logger.info(f"Scanner: Indexed {len(chunks)} passage vectors in FAISS for file ID {file_id}")
            
        finally:
            conn.close()

    @classmethod
    def purge_deleted_files(cls, custom_db_path: Optional[str] = None) -> int:
        """
        Removes vectors and updates indexing_status = 'DELETED' for files that were
        removed from disk or whose folder authorization was revoked.
        """
        conn = get_db_connection(custom_db_path)
        cursor = conn.cursor()
        purged_count = 0
        try:
            cursor.execute("SELECT id, file_path FROM files WHERE indexing_status != 'DELETED'")
            records = [dict(r) for r in cursor.fetchall()]
            
            for rec in records:
                path = rec["file_path"]
                if not os.path.exists(path) or not FolderGuard.is_path_authorized(path, db_path=custom_db_path):
                    cls._clear_file_vectors(rec["id"], custom_db_path=custom_db_path)
                    cursor.execute("UPDATE files SET indexing_status = 'DELETED' WHERE id = ?", (rec["id"],))
                    purged_count += 1
                    logger.info(f"Scanner: Purged deleted/unauthorized file from index: {path}")
                    
            conn.commit()
            return purged_count
        finally:
            conn.close()

    @classmethod
    def scan_all_authorized_folders(cls, custom_db_path: Optional[str] = None) -> Dict[str, Any]:
        # Purge deleted or unauthorized files first
        cls.purge_deleted_files(custom_db_path=custom_db_path)

        authorized_records = get_authorized_folders(active_only=True, custom_db_path=custom_db_path)
        total_scanned = 0
        successful = 0
        skipped = 0
        failed = 0

        for record in authorized_records:
            folder_path = record["folder_path"]
            is_recursive = bool(record.get("is_recursive", 1))

            if not os.path.exists(folder_path):
                continue

            for root, _, files in os.walk(folder_path) if is_recursive else [(folder_path, [], os.listdir(folder_path))]:
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        full_path = os.path.join(root, file)
                        total_scanned += 1
                        res = cls.scan_file(full_path, custom_db_path=custom_db_path)
                        if res:
                            if res.get("indexing_status") == "SKIPPED":
                                skipped += 1
                            else:
                                successful += 1
                        else:
                            failed += 1

        return {
            "total_scanned": total_scanned,
            "successful": successful,
            "skipped": skipped,
            "failed": failed
        }
