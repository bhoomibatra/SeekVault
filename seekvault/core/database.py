import os
import sqlite3
from typing import List, Dict, Any, Optional
from seekvault.config import DB_PATH
from seekvault.core.logger import logger

def get_db_connection(custom_db_path: Optional[str] = None) -> sqlite3.Connection:
    target_path = custom_db_path or DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(custom_db_path: Optional[str] = None) -> None:
    conn = get_db_connection(custom_db_path)
    cursor = conn.cursor()
    
    schema_sql = """
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS authorized_folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folder_path TEXT NOT NULL UNIQUE,
        is_recursive INTEGER NOT NULL DEFAULT 1,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS version_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_file_id INTEGER,
        group_name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL UNIQUE,
        file_name TEXT NOT NULL,
        file_extension TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        mime_type TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        modified_at TIMESTAMP NOT NULL,
        sha256_hash TEXT NOT NULL,
        phash TEXT,
        file_type TEXT CHECK(file_type IN ('document', 'image', 'other')) NOT NULL,
        privacy_tier TEXT CHECK(privacy_tier IN ('FULL', 'REDACTED', 'METADATA_ONLY')) NOT NULL DEFAULT 'FULL',
        indexing_status TEXT CHECK(indexing_status IN ('PENDING', 'INDEXED', 'FAILED', 'SKIPPED', 'DELETED')) NOT NULL DEFAULT 'PENDING',
        version_group_id INTEGER,
        is_canonical INTEGER DEFAULT 1,
        error_message TEXT,
        extracted_text TEXT,
        extraction_method TEXT,
        extraction_status TEXT,
        last_indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (version_group_id) REFERENCES version_groups(id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_files_sha256 ON files(sha256_hash);
    CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path);
    CREATE INDEX IF NOT EXISTS idx_files_status ON files(indexing_status);
    CREATE INDEX IF NOT EXISTS idx_files_ext ON files(file_extension);

    CREATE TABLE IF NOT EXISTS document_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        page_number INTEGER DEFAULT 1,
        start_char_idx INTEGER,
        end_char_idx INTEGER,
        raw_text TEXT,
        redacted_text TEXT,
        presidio_entities_json TEXT,
        vector_faiss_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS image_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL UNIQUE,
        width INTEGER NOT NULL,
        height INTEGER NOT NULL,
        format TEXT NOT NULL,
        channels INTEGER,
        ocr_raw_text TEXT,
        ocr_redacted_text TEXT,
        presidio_entities_json TEXT,
        text_vector_faiss_id INTEGER,
        visual_vector_faiss_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS faiss_index_mapping (
        faiss_vector_id INTEGER PRIMARY KEY,
        index_type TEXT CHECK(index_type IN ('text', 'visual')) NOT NULL,
        entity_type TEXT CHECK(entity_type IN ('document_chunk', 'image_metadata')) NOT NULL,
        entity_id INTEGER NOT NULL,
        file_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS file_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        parent_file_id INTEGER NOT NULL,
        child_file_id INTEGER NOT NULL,
        similarity_score REAL NOT NULL,
        relation_type TEXT CHECK(relation_type IN ('exact_duplicate', 'near_duplicate', 'newer_version')) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES version_groups(id) ON DELETE CASCADE,
        FOREIGN KEY (parent_file_id) REFERENCES files(id) ON DELETE CASCADE,
        FOREIGN KEY (child_file_id) REFERENCES files(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS privacy_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        detected_pii_types_json TEXT NOT NULL,
        sensitivity_score REAL NOT NULL,
        applied_tier TEXT CHECK(applied_tier IN ('FULL', 'REDACTED', 'METADATA_ONLY')) NOT NULL,
        scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
    );
    """
    
    cursor.executescript(schema_sql)

    # Migrations for schema updates
    for col_def in ["extracted_text TEXT", "extraction_method TEXT", "extraction_status TEXT"]:
        try:
            cursor.execute(f"ALTER TABLE files ADD COLUMN {col_def};")
        except Exception:
            pass

    conn.commit()
    conn.close()
    logger.info("SQLite Database initialized successfully.")

# CRUD Helpers for Authorized Folders
def add_authorized_folder(folder_path: str, is_recursive: bool = True, custom_db_path: Optional[str] = None) -> Dict[str, Any]:
    norm_path = os.path.abspath(os.path.realpath(folder_path))
    if not os.path.exists(norm_path) or not os.path.isdir(norm_path):
        raise ValueError(f"Directory '{folder_path}' does not exist or is not a valid folder.")
        
    conn = get_db_connection(custom_db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO authorized_folders (folder_path, is_recursive, is_active, updated_at)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(folder_path) DO UPDATE SET is_active = 1, updated_at = CURRENT_TIMESTAMP
            """,
            (norm_path, 1 if is_recursive else 0)
        )
        conn.commit()
        folder_id = cursor.lastrowid
        logger.info(f"Authorized folder added/activated: {norm_path}")
        return {"id": folder_id, "folder_path": norm_path, "is_recursive": is_recursive, "is_active": True}
    finally:
        conn.close()

def remove_authorized_folder(folder_id: int, custom_db_path: Optional[str] = None) -> bool:
    conn = get_db_connection(custom_db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE authorized_folders SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (folder_id,))
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Deactivated authorized folder ID: {folder_id}")
        return success
    finally:
        conn.close()

def get_authorized_folders(active_only: bool = True, custom_db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection(custom_db_path)
    cursor = conn.cursor()
    try:
        if active_only:
            cursor.execute("SELECT * FROM authorized_folders WHERE is_active = 1 ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM authorized_folders ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

# CRUD Helpers for Files Metadata & Extraction Results
def upsert_file_metadata(file_record: Dict[str, Any], custom_db_path: Optional[str] = None) -> int:
    conn = get_db_connection(custom_db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO files (
                file_path, file_name, file_extension, file_size, mime_type,
                created_at, modified_at, sha256_hash, phash, file_type,
                privacy_tier, indexing_status, error_message,
                extracted_text, extraction_method, extraction_status,
                last_indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(file_path) DO UPDATE SET
                file_name = excluded.file_name,
                file_extension = excluded.file_extension,
                file_size = excluded.file_size,
                mime_type = excluded.mime_type,
                modified_at = excluded.modified_at,
                sha256_hash = excluded.sha256_hash,
                phash = excluded.phash,
                file_type = excluded.file_type,
                indexing_status = excluded.indexing_status,
                error_message = excluded.error_message,
                extracted_text = excluded.extracted_text,
                extraction_method = excluded.extraction_method,
                extraction_status = excluded.extraction_status,
                last_indexed_at = CURRENT_TIMESTAMP
            """,
            (
                file_record["file_path"],
                file_record["file_name"],
                file_record["file_extension"].lower(),
                file_record["file_size"],
                file_record.get("mime_type", "application/octet-stream"),
                file_record["created_at"],
                file_record["modified_at"],
                file_record["sha256_hash"],
                file_record.get("phash"),
                file_record["file_type"],
                file_record.get("privacy_tier", "FULL"),
                file_record.get("indexing_status", "INDEXED"),
                file_record.get("error_message"),
                file_record.get("extracted_text", ""),
                file_record.get("extraction_method", "none"),
                file_record.get("extraction_status", "PENDING")
            )
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_indexed_files(
    limit: int = 100,
    offset: int = 0,
    file_type: Optional[str] = None,
    custom_db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_db_connection(custom_db_path)
    cursor = conn.cursor()
    try:
        if file_type and file_type != "All":
            cursor.execute(
                "SELECT * FROM files WHERE indexing_status != 'DELETED' AND file_type = ? ORDER BY modified_at DESC LIMIT ? OFFSET ?",
                (file_type, limit, offset)
            )
        else:
            cursor.execute(
                "SELECT * FROM files WHERE indexing_status != 'DELETED' ORDER BY modified_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def log_privacy_audit(
    file_id: int,
    detected_entities: List[Dict[str, Any]],
    sensitivity_score: float,
    applied_tier: str,
    custom_db_path: Optional[str] = None
) -> int:
    import json
    conn = get_db_connection(custom_db_path)
    cursor = conn.cursor()
    try:
        entities_json = json.dumps(detected_entities)
        cursor.execute(
            """
            INSERT INTO privacy_audit_logs (file_id, detected_pii_types_json, sensitivity_score, applied_tier)
            VALUES (?, ?, ?, ?)
            """,
            (file_id, entities_json, sensitivity_score, applied_tier)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_dashboard_stats(custom_db_path: Optional[str] = None) -> Dict[str, Any]:
    conn = get_db_connection(custom_db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM authorized_folders WHERE is_active = 1")
        total_folders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM files WHERE indexing_status != 'DELETED'")
        row = cursor.fetchone()
        total_files = row[0]
        total_size = row[1]
        
        cursor.execute("SELECT file_type, COUNT(*) FROM files WHERE indexing_status != 'DELETED' GROUP BY file_type")
        type_counts = dict(cursor.fetchall())
        
        cursor.execute("SELECT file_extension, COUNT(*) FROM files WHERE indexing_status != 'DELETED' GROUP BY file_extension")
        ext_counts = dict(cursor.fetchall())
        
        return {
            "total_folders": total_folders,
            "total_files": total_files,
            "total_size_bytes": total_size,
            "type_counts": type_counts,
            "ext_counts": ext_counts
        }
    finally:
        conn.close()
