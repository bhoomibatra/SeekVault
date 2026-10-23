import os
import json
import hashlib
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from seekvault.database.connection import get_db_connection
from seekvault.database.schema import init_db

logger = logging.getLogger(__name__)

class Repository:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            from seekvault.config import DB_PATH
            db_path = DB_PATH
        self.db_path = db_path
        # Initialize or migrate the schema safely
        with self._get_conn() as conn:
            init_db(conn, db_path=self.db_path)


    def _get_conn(self):
        if self.db_path:
            return get_db_connection(self.db_path)
        return get_db_connection()

    # -------------------------------------------------------------
    # Authorized Folders
    # -------------------------------------------------------------
    @staticmethod
    def _validate_folder_path(folder_path: str) -> tuple:
        """Validate and resolve a folder path for safe authorization.

        Returns (resolved_norm_path, error_message_or_None).
        Resolves symlinks where present so the stored path points to the real physical location.
        Rejects paths that aren't absolute or use reserved Windows device names.
        """
        p = Path(folder_path)

        # Must be an absolute path
        if not p.is_absolute():
            return None, f"Path must be absolute: '{folder_path}'"

        # Resolve symlinks where present
        try:
            real_p = p.resolve()
        except (OSError, RuntimeError) as exc:
            return None, f"Path cannot be resolved: '{folder_path}' — {exc}"

        if real_p.exists() and not real_p.is_dir():
            return None, f"Path is not a directory: '{real_p}'"

        # Windows: reject reserved device names
        reserved = {"CON", "PRN", "AUX", "NUL",
                    "COM1", "COM2", "COM3", "COM4", "COM5",
                    "COM6", "COM7", "COM8", "COM9",
                    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
                    "LPT6", "LPT7", "LPT8", "LPT9"}
        if real_p.name.upper() in reserved:
            return None, f"Path name is a reserved Windows device name: '{real_p.name}'"

        norm_path = os.path.normcase(os.path.normpath(str(real_p)))
        return norm_path, None

    def add_authorized_folder(self, folder_path: str, is_recursive: bool = True) -> int:
        """Authorize a folder for indexing.  Resolves symlinks before storing so
        the containment check is always against real filesystem paths."""
        norm_path, error = self._validate_folder_path(folder_path)
        if error:
            logger.warning("add_authorized_folder rejected: %s", error)
            raise ValueError(error)
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO authorized_folders (folder_path, is_recursive, is_active, updated_at)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(folder_path) DO UPDATE SET
                    is_active = 1,
                    is_recursive = excluded.is_recursive,
                    updated_at = CURRENT_TIMESTAMP
            """, (norm_path, 1 if is_recursive else 0))
            return cursor.lastrowid or 0

    def get_folder_file_counts(self) -> dict:
        """Return {folder_id: (indexed_count, failed_count, pending_count)} for all folders."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT folder_id,
                       SUM(CASE WHEN status = 'INDEXED'  THEN 1 ELSE 0 END) AS indexed_count,
                       SUM(CASE WHEN status = 'FAILED'   THEN 1 ELSE 0 END) AS failed_count,
                       SUM(CASE WHEN status = 'PENDING'  THEN 1 ELSE 0 END) AS pending_count
                FROM files
                GROUP BY folder_id
            """)
            return {
                row["folder_id"]: {
                    "indexed": row["indexed_count"] or 0,
                    "failed":  row["failed_count"]  or 0,
                    "pending": row["pending_count"] or 0,
                }
                for row in cursor.fetchall()
            }

    def remove_authorized_folder(self, folder_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM authorized_folders WHERE id = ?", (folder_id,))
            return cursor.rowcount > 0

    def set_folder_active_state(self, folder_id: int, is_active: bool) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE authorized_folders
                SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (1 if is_active else 0, folder_id))
            return cursor.rowcount > 0

    def get_authorized_folders(self, active_only: bool = False) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM authorized_folders"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY id ASC"
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def is_path_authorized(self, file_path: str) -> bool:
        """Verify if a given file path is located inside any active authorized folder.

        Enforces:
        1. Path-aware containment (not naive string-prefix checks) to block sibling prefixes.
        2. Windows path normalization and case-folding.
        3. Symlink and junction escape prevention: if the path or any parent is a link,
           its resolved physical target must also reside within an authorized folder.
        """
        try:
            p = Path(file_path)
            abs_p = Path(os.path.normcase(os.path.normpath(os.path.abspath(file_path))))
        except Exception:
            return False

        folders = self.get_authorized_folders(active_only=True)
        if not folders:
            return False

        norm_folders = []
        for f in folders:
            f_norm = Path(os.path.normcase(os.path.normpath(f["folder_path"])))
            norm_folders.append((f_norm, bool(f["is_recursive"])))

        # 1. Lexical path-aware containment check
        lexically_authorized = False
        for f_norm, is_recursive in norm_folders:
            if is_recursive:
                if abs_p == f_norm or f_norm in abs_p.parents:
                    lexically_authorized = True
                    break
            else:
                if abs_p.parent == f_norm:
                    lexically_authorized = True
                    break

        if not lexically_authorized:
            return False

        # 2. Symlink / junction resolution check (prevent boundary escape)
        try:
            if p.exists():
                resolved_p = Path(os.path.normcase(os.path.normpath(str(p.resolve()))))
                target_authorized = False
                for f_norm, is_recursive in norm_folders:
                    if is_recursive:
                        if resolved_p == f_norm or f_norm in resolved_p.parents:
                            target_authorized = True
                            break
                    else:
                        if resolved_p.parent == f_norm:
                            target_authorized = True
                            break
                if not target_authorized:
                    logger.warning(
                        "Symlink/junction escape attempt blocked: '%s' resolves to '%s' (outside authorized roots)",
                        file_path, resolved_p
                    )
                    return False
        except (OSError, RuntimeError) as exc:
            logger.warning("Could not resolve path '%s': %s", file_path, exc)
            return False

        return True

    def get_folder_for_path(self, file_path: str) -> Optional[int]:
        """Return the folder ID that contains file_path, using path-aware containment."""
        try:
            norm_file = Path(os.path.normcase(os.path.normpath(os.path.abspath(file_path))))
        except Exception:
            return None

        folders = self.get_authorized_folders(active_only=True)
        # Sort folders by path length descending so the most specific (deepest nested) folder matches first
        folders = sorted(folders, key=lambda f: len(f["folder_path"]), reverse=True)
        for f in folders:
            folder_dir = Path(os.path.normcase(os.path.normpath(f["folder_path"])))
            is_recursive = bool(f["is_recursive"])
            if is_recursive:
                if norm_file == folder_dir or folder_dir in norm_file.parents:
                    return f["id"]
            else:
                if norm_file.parent == folder_dir:
                    return f["id"]
        return None

    # -------------------------------------------------------------
    # Files
    # -------------------------------------------------------------
    def upsert_file(
        self,
        folder_id: Optional[int],
        file_path: str,
        file_name: str,
        file_extension: str,
        file_size: int,
        file_hash: str,
        file_type: str,
        modified_at: str,
        privacy_tier: str = "FULL",
        status: str = "PENDING",   # starts as PENDING; pipeline sets INDEXED or FAILED
        visual_metadata: Optional[Dict[str, Any]] = None,
        error_detail: Optional[str] = None
    ) -> int:
        norm_path = os.path.normpath(os.path.abspath(file_path))
        v_meta_json = json.dumps(visual_metadata) if visual_metadata else None
        err_str = error_detail[:1000] if error_detail else None
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO files (
                    folder_id, file_path, file_name, file_extension,
                    file_size, file_hash, file_type, modified_at,
                    privacy_tier, status, visual_metadata, error_detail, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(file_path) DO UPDATE SET
                    folder_id       = excluded.folder_id,
                    file_size       = excluded.file_size,
                    file_hash       = excluded.file_hash,
                    file_type       = excluded.file_type,
                    modified_at     = excluded.modified_at,
                    privacy_tier    = excluded.privacy_tier,
                    status          = excluded.status,
                    visual_metadata = excluded.visual_metadata,
                    error_detail    = excluded.error_detail,
                    indexed_at      = CURRENT_TIMESTAMP
            """, (
                folder_id, norm_path, file_name, file_extension,
                file_size, file_hash, file_type, modified_at,
                privacy_tier, status, v_meta_json, err_str
            ))
            cursor.execute("SELECT id FROM files WHERE file_path = ?", (norm_path,))
            row = cursor.fetchone()
            return row["id"] if row else 0

    def update_file_status(self, file_id: int, status: str) -> bool:
        """Update a file's indexing lifecycle status (PENDING/INDEXED/FAILED/UNAUTHORIZED)."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE files SET status = ?, indexed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, file_id)
            )
            return cursor.rowcount > 0

    def update_file_error(self, file_id: int, error_detail: str) -> bool:
        """Mark a file as FAILED and record the extraction error detail."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE files SET status = 'FAILED', error_detail = ?, indexed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (error_detail[:1000], file_id)
            )
            return cursor.rowcount > 0

    def reset_pending_files(self) -> int:
        """Reset all FAILED files back to PENDING so they can be retried."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE files SET status = 'PENDING', error_detail = NULL WHERE status = 'FAILED'"
            )
            return cursor.rowcount

    def get_failed_files(self) -> List[Dict[str, Any]]:
        """Retrieve all file records with status='FAILED' for transparent error reporting."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.*, af.folder_path as folder_root
                FROM files f
                LEFT JOIN authorized_folders af ON f.folder_id = af.id
                WHERE f.status = 'FAILED'
                ORDER BY f.indexed_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]



    def get_file_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            if row:
                res = dict(row)
                if res.get("visual_metadata"):
                    try:
                        res["visual_metadata"] = json.loads(res["visual_metadata"])
                    except Exception:
                        pass
                return res
            return None

    def get_file_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        norm_path = os.path.normpath(os.path.abspath(file_path))
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE file_path = ?", (norm_path,))
            row = cursor.fetchone()
            if row:
                res = dict(row)
                if res.get("visual_metadata"):
                    try:
                        res["visual_metadata"] = json.loads(res["visual_metadata"])
                    except Exception:
                        pass
                return res
            return None

    def delete_file_by_path(self, file_path: str) -> bool:
        norm_path = os.path.normpath(os.path.abspath(file_path))
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE file_path = ?", (norm_path,))
            return cursor.rowcount > 0

    def get_all_indexed_files(
        self,
        limit: int = 100,
        offset: int = 0,
        file_type: Optional[str] = None,
        privacy_tier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            query = "SELECT f.*, fc.raw_char_count, fc.has_ocr FROM files f LEFT JOIN file_content fc ON f.id = fc.file_id WHERE 1=1"
            params: List[Any] = []
            if file_type:
                query += " AND f.file_type = ?"
                params.append(file_type)
            if privacy_tier:
                query += " AND f.privacy_tier = ?"
                params.append(privacy_tier)
            query += " ORDER BY f.indexed_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def get_all_files(self, status: Optional[str] = "INDEXED") -> List[Dict[str, Any]]:
        """Retrieve all file records, optionally filtered by status."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM files WHERE status = ?", (status,))
            else:
                cursor.execute("SELECT * FROM files")
            return [dict(r) for r in cursor.fetchall()]

    def prune_missing_files(self) -> List[int]:
        """Scan SQLite file records and purge any whose physical file is missing from disk
        or whose parent folder is no longer authorized. Returns list of purged file IDs."""
        purged_ids: List[int] = []
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, file_path FROM files")
            records = [dict(row) for row in cursor.fetchall()]

        for r in records:
            fid = r["id"]
            fpath = r["file_path"]
            if not os.path.exists(fpath) or not self.is_path_authorized(fpath):
                with self._get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM files WHERE id = ?", (fid,))
                    if cursor.rowcount > 0:
                        purged_ids.append(fid)

        return purged_ids


    # -------------------------------------------------------------
    # Content & Privacy Entities
    # -------------------------------------------------------------
    def save_file_content(
        self,
        file_id: int,
        raw_char_count: int,
        searchable_text_preview: str,
        redacted_preview: str,
        has_ocr: bool = False
    ) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO file_content (
                    file_id, raw_char_count, searchable_text_preview,
                    redacted_preview, has_ocr
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(file_id) DO UPDATE SET
                    raw_char_count = excluded.raw_char_count,
                    searchable_text_preview = excluded.searchable_text_preview,
                    redacted_preview = excluded.redacted_preview,
                    has_ocr = excluded.has_ocr
            """, (
                file_id, raw_char_count, searchable_text_preview[:2000],
                redacted_preview[:2000], 1 if has_ocr else 0
            ))
            # Keep FTS5 index in sync: delete stale entry then re-insert
            try:
                cursor.execute(
                    "DELETE FROM file_content_fts WHERE file_id = ?", (file_id,)
                )
                cursor.execute(
                    "INSERT INTO file_content_fts(file_id, searchable_text_preview) VALUES (?, ?)",
                    (file_id, searchable_text_preview[:2000])
                )
            except Exception as fts_exc:
                # FTS table may not exist on first run before migration; log and continue
                logger.debug("FTS sync skipped for file_id=%d: %s", file_id, fts_exc)

    def get_file_content(self, file_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_content WHERE file_id = ?", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_detected_entities(self, file_id: int, entities: List[Dict[str, Any]]) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Clear old entities for this file before reinserting
            cursor.execute("DELETE FROM detected_entities WHERE file_id = ?", (file_id,))
            for ent in entities:
                ent_type = ent.get("entity_type", "UNKNOWN")
                raw_text = ent.get("entity_text", "")
                if ent.get("entity_token") and ent["entity_token"] != raw_text:
                    entity_token = ent["entity_token"]
                elif raw_text:
                    h = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:6]
                    entity_token = f"<{ent_type}_REDACTED_{h}>"
                else:
                    entity_token = f"<{ent_type}_REDACTED>"

                if len(entity_token) > 64:
                    entity_token = f"<{ent_type}_REDACTED>"

                cursor.execute("""
                    INSERT INTO detected_entities (
                        file_id, entity_type, entity_token, confidence
                    ) VALUES (?, ?, ?, ?)
                """, (
                    file_id,
                    ent_type,
                    entity_token,
                    ent.get("confidence", 1.0),
                ))



    def get_detected_entities_for_file(self, file_id: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM detected_entities WHERE file_id = ?", (file_id,))
            return [dict(r) for r in cursor.fetchall()]

    # -------------------------------------------------------------
    # Full-Text Search (FTS5)
    # -------------------------------------------------------------
    def fts_search_content(
        self,
        query: str,
        top_k: int = 20,
        folder_ids: Optional[List[int]] = None,
        file_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Keyword search using SQLite FTS5 on file content previews.

        Returns a list of dicts with keys:
          file_id, score (bm25, negated so lower=better), file_rec fields,
          and 'excerpt' from the FTS snippet function.

        ``folder_ids`` and ``file_types`` are optional allow-lists applied
        before returning results.  Only INDEXED files in active authorized
        folders are returned.
        """
        if not query or not query.strip():
            return []

        # Escape FTS5 special characters in the query so literal phrases work
        safe_query = query.replace('"', '""')

        with self._get_conn() as conn:
            cursor = conn.cursor()

            # Build optional filter clauses
            extra_where = "AND f.status = 'INDEXED' AND af.is_active = 1"
            params: List[Any] = [safe_query]

            if folder_ids:
                placeholders = ",".join(["?"] * len(folder_ids))
                extra_where += f" AND f.folder_id IN ({placeholders})"
                params.extend(folder_ids)

            if file_types:
                placeholders = ",".join(["?"] * len(file_types))
                extra_where += f" AND f.file_type IN ({placeholders})"
                params.extend(file_types)

            params.append(top_k)

            sql = f"""
                SELECT
                    fts.file_id,
                    bm25(file_content_fts)            AS bm25_score,
                    snippet(
                        file_content_fts, 1,
                        '<b>', '</b>', '...', 20
                    )                                 AS excerpt,
                    f.file_name,
                    f.file_path,
                    f.file_extension,
                    f.file_size,
                    f.file_type,
                    f.modified_at,
                    f.privacy_tier,
                    f.status,
                    f.visual_metadata
                FROM file_content_fts fts
                JOIN files f ON f.id = fts.file_id
                JOIN authorized_folders af ON af.id = f.folder_id
                WHERE file_content_fts MATCH ?
                {extra_where}
                ORDER BY bm25_score
                LIMIT ?
            """

            try:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            except Exception as exc:
                logger.warning("FTS search failed: %s", exc)
                return []

            results = []
            for row in rows:
                rec = dict(row)
                if rec.get("visual_metadata"):
                    try:
                        rec["visual_metadata"] = json.loads(rec["visual_metadata"])
                    except Exception:
                        pass
                # Convert BM25 score (negative in SQLite) to a positive relevance signal
                rec["fts_score"] = abs(float(rec.pop("bm25_score", 0) or 0))
                results.append(rec)

            return results

    def get_files_by_ids_filtered(
        self,
        file_ids: List[int],
        folder_ids: Optional[List[int]] = None,
        file_types: Optional[List[str]] = None
    ) -> Dict[int, Dict[str, Any]]:
        """Fetch file records for a set of IDs and apply optional filters.

        Returns a dict mapping file_id → file record dict.  Only INDEXED
        files in active authorized folders are included.
        """
        if not file_ids:
            return {}

        with self._get_conn() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(file_ids))
            params: List[Any] = list(file_ids)

            extra_where = "AND f.status = 'INDEXED' AND af.is_active = 1"

            if folder_ids:
                ph = ",".join(["?"] * len(folder_ids))
                extra_where += f" AND f.folder_id IN ({ph})"
                params.extend(folder_ids)

            if file_types:
                ph = ",".join(["?"] * len(file_types))
                extra_where += f" AND f.file_type IN ({ph})"
                params.extend(file_types)

            sql = f"""
                SELECT f.* FROM files f
                JOIN authorized_folders af ON af.id = f.folder_id
                WHERE f.id IN ({placeholders})
                {extra_where}
            """
            cursor.execute(sql, params)
            out: Dict[int, Dict[str, Any]] = {}
            for row in cursor.fetchall():
                rec = dict(row)
                if rec.get("visual_metadata"):
                    try:
                        rec["visual_metadata"] = json.loads(rec["visual_metadata"])
                    except Exception:
                        pass
                out[rec["id"]] = rec
            return out

    def get_all_detected_entities(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.*, f.file_name, f.file_path, f.privacy_tier
                FROM detected_entities e
                JOIN files f ON e.file_id = f.id
                ORDER BY e.id DESC
            """)
            return [dict(r) for r in cursor.fetchall()]

    # -------------------------------------------------------------
    # Vector Mappings
    # -------------------------------------------------------------
    def clear_vector_mappings(self, file_id: int, modality: Optional[str] = None) -> int:
        """Clear recorded vector mappings for a file before re-embedding."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            if modality:
                cursor.execute("DELETE FROM vector_mappings WHERE file_id = ? AND modality = ?", (file_id, modality))
            else:
                cursor.execute("DELETE FROM vector_mappings WHERE file_id = ?", (file_id,))
            return cursor.rowcount

    def save_vector_mapping(self, file_id: int, modality: str, faiss_vector_id: int, vector_dim: int) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vector_mappings (file_id, modality, faiss_vector_id, vector_dim)
                VALUES (?, ?, ?, ?)
            """, (file_id, modality, faiss_vector_id, vector_dim))
            return cursor.lastrowid or 0

    def get_vectors_for_file(self, file_id: int) -> List[Dict[str, Any]]:
        """Retrieve all vector mappings for a specific file across all chunks."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vector_mappings WHERE file_id = ? ORDER BY id ASC", (file_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_file_by_vector_id(self, modality: str, faiss_vector_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.* FROM files f
                JOIN vector_mappings vm ON f.id = vm.file_id
                WHERE vm.modality = ? AND vm.faiss_vector_id = ?
            """, (modality, faiss_vector_id))
            row = cursor.fetchone()
            if row:
                res = dict(row)
                if res.get("visual_metadata"):
                    try:
                        res["visual_metadata"] = json.loads(res["visual_metadata"])
                    except Exception:
                        pass
                return res
            return None

    # -------------------------------------------------------------
    # Duplicates & Versions
    # -------------------------------------------------------------
    def get_duplicate_groups(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_hash, COUNT(*) as file_count, SUM(file_size) as total_size,
                       GROUP_CONCAT(id) as file_ids,
                       GROUP_CONCAT(file_name, ' | ') as file_names,
                       GROUP_CONCAT(file_path, ';;;') as file_paths
                FROM files
                GROUP BY file_hash
                HAVING COUNT(*) > 1
                ORDER BY total_size DESC
            """)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append({
                    "file_hash": r["file_hash"],
                    "file_count": r["file_count"],
                    "total_size": r["total_size"],
                    "file_ids": [int(x) for x in r["file_ids"].split(",")],
                    "file_names": r["file_names"].split(" | "),
                    "file_paths": r["file_paths"].split(";;;"),
                    "reclaimable_size": r["total_size"] - (r["total_size"] // r["file_count"])
                })
            return results

    def save_version_group(self, group_name: str, member_tuples: List[Tuple[int, float, int]]) -> int:
        """member_tuples is a list of (file_id, similarity_score, version_order)"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            base_file_id = member_tuples[0][0] if member_tuples else None
            cursor.execute("""
                INSERT INTO version_groups (group_name, base_file_id)
                VALUES (?, ?)
            """, (group_name, base_file_id))
            vg_id = cursor.lastrowid or 0
            for file_id, sim, order in member_tuples:
                cursor.execute("""
                    INSERT INTO version_members (version_group_id, file_id, similarity_score, version_order)
                    VALUES (?, ?, ?, ?)
                """, (vg_id, file_id, sim, order))
            return vg_id

    def clear_version_groups(self) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM version_members")
            conn.execute("DELETE FROM version_groups")

    def get_all_version_groups(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM version_groups ORDER BY id ASC")
            v_groups = [dict(r) for r in cursor.fetchall()]
            for vg in v_groups:
                cursor.execute("""
                    SELECT vm.*, f.file_name, f.file_path, f.modified_at, f.file_size
                    FROM version_members vm
                    JOIN files f ON vm.file_id = f.id
                    WHERE vm.version_group_id = ?
                    ORDER BY vm.version_order ASC
                """, (vg["id"],))
                vg["members"] = [dict(r) for r in cursor.fetchall()]
            return v_groups

    # -------------------------------------------------------------
    # Dashboard & Telemetry
    # -------------------------------------------------------------
    def get_dashboard_stats(self) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM authorized_folders WHERE is_active = 1")
            active_folders = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM files")
            total_files = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM files WHERE file_type = 'DOCUMENT'")
            doc_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM files WHERE file_type = 'IMAGE'")
            img_count = cursor.fetchone()[0]

            cursor.execute("SELECT privacy_tier, COUNT(*) as count FROM files GROUP BY privacy_tier")
            tier_rows = cursor.fetchall()
            tier_counts = {r["privacy_tier"]: r["count"] for r in tier_rows}

            cursor.execute("SELECT COUNT(*) FROM (SELECT file_hash FROM files GROUP BY file_hash HAVING COUNT(*) > 1)")
            duplicate_clusters = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM version_groups")
            version_groups_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM detected_entities")
            total_pii_entities = cursor.fetchone()[0]

            return {
                "active_folders": active_folders,
                "total_files": total_files,
                "document_count": doc_count,
                "image_count": img_count,
                "tier_counts": tier_counts,
                "duplicate_clusters": duplicate_clusters,
                "version_groups_count": version_groups_count,
                "total_pii_entities": total_pii_entities
            }
