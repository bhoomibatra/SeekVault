import os
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from seekvault.database.connection import get_db_connection
from seekvault.database.schema import init_db

class Repository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        # Ensure database tables exist
        with self._get_conn() as conn:
            init_db(conn)

    def _get_conn(self):
        if self.db_path:
            return get_db_connection(self.db_path)
        return get_db_connection()

    # -------------------------------------------------------------
    # Authorized Folders
    # -------------------------------------------------------------
    def add_authorized_folder(self, folder_path: str, is_recursive: bool = True) -> int:
        # Normalize and case-fold the stored path so all downstream comparisons
        # are immune to Windows drive-letter / directory casing differences.
        norm_path = os.path.normcase(os.path.normpath(os.path.abspath(folder_path)))
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

        Uses os.path.normcase so that drive-letter and directory-name casing
        differences on Windows never produce a false-negative authorization result.
        """
        norm_file = os.path.normcase(os.path.normpath(os.path.abspath(file_path)))
        folders = self.get_authorized_folders(active_only=True)
        for f in folders:
            # Stored paths were already normcase'd at insert time, but apply
            # normcase here too so existing records without the update still work.
            folder_dir = os.path.normcase(os.path.normpath(f["folder_path"]))
            is_recursive = bool(f["is_recursive"])
            if is_recursive:
                if norm_file.startswith(folder_dir + os.sep) or norm_file == folder_dir:
                    return True
            else:
                if os.path.normcase(os.path.dirname(norm_file)) == folder_dir:
                    return True
        return False

    def get_folder_for_path(self, file_path: str) -> Optional[int]:
        """Return the folder ID that contains file_path, using case-insensitive comparison."""
        norm_file = os.path.normcase(os.path.normpath(os.path.abspath(file_path)))
        folders = self.get_authorized_folders(active_only=True)
        for f in folders:
            folder_dir = os.path.normcase(os.path.normpath(f["folder_path"]))
            is_recursive = bool(f["is_recursive"])
            if is_recursive and (norm_file.startswith(folder_dir + os.sep) or norm_file == folder_dir):
                return f["id"]
            elif not is_recursive and os.path.normcase(os.path.dirname(norm_file)) == folder_dir:
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
        status: str = "INDEXED",
        visual_metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        norm_path = os.path.normpath(os.path.abspath(file_path))
        v_meta_json = json.dumps(visual_metadata) if visual_metadata else None
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO files (
                    folder_id, file_path, file_name, file_extension,
                    file_size, file_hash, file_type, modified_at,
                    privacy_tier, status, visual_metadata, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(file_path) DO UPDATE SET
                    folder_id = excluded.folder_id,
                    file_size = excluded.file_size,
                    file_hash = excluded.file_hash,
                    file_type = excluded.file_type,
                    modified_at = excluded.modified_at,
                    privacy_tier = excluded.privacy_tier,
                    status = excluded.status,
                    visual_metadata = excluded.visual_metadata,
                    indexed_at = CURRENT_TIMESTAMP
            """, (
                folder_id, norm_path, file_name, file_extension,
                file_size, file_hash, file_type, modified_at,
                privacy_tier, status, v_meta_json
            ))
            cursor.execute("SELECT id FROM files WHERE file_path = ?", (norm_path,))
            row = cursor.fetchone()
            return row["id"] if row else 0

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

    def get_file_content(self, file_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_content WHERE file_id = ?", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_detected_entities(self, file_id: int, entities: List[Dict[str, Any]]) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # Clear old entities for this file
            cursor.execute("DELETE FROM detected_entities WHERE file_id = ?", (file_id,))
            for ent in entities:
                cursor.execute("""
                    INSERT INTO detected_entities (
                        file_id, entity_type, entity_text, confidence, start_char, end_char
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    file_id,
                    ent.get("entity_type", "UNKNOWN"),
                    ent.get("entity_text", ""),
                    ent.get("confidence", 1.0),
                    ent.get("start_char", 0),
                    ent.get("end_char", 0)
                ))

    def get_detected_entities_for_file(self, file_id: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM detected_entities WHERE file_id = ?", (file_id,))
            return [dict(r) for r in cursor.fetchall()]

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
    def save_vector_mapping(self, file_id: int, modality: str, faiss_vector_id: int, vector_dim: int) -> int:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM vector_mappings WHERE file_id = ? AND modality = ?
            """, (file_id, modality))
            cursor.execute("""
                INSERT INTO vector_mappings (file_id, modality, faiss_vector_id, vector_dim)
                VALUES (?, ?, ?, ?)
            """, (file_id, modality, faiss_vector_id, vector_dim))
            return cursor.lastrowid or 0

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
