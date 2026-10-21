import sqlite3
import logging

logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = """
-- Table: authorized_folders
CREATE TABLE IF NOT EXISTS authorized_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT UNIQUE NOT NULL,
    is_recursive INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: files
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id INTEGER,
    file_path TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    file_extension TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash TEXT NOT NULL,
    file_type TEXT NOT NULL, -- 'DOCUMENT' or 'IMAGE'
    modified_at TIMESTAMP NOT NULL,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    privacy_tier TEXT NOT NULL DEFAULT 'FULL', -- 'FULL', 'REDACTED', 'METADATA_ONLY'
    status TEXT NOT NULL DEFAULT 'INDEXED', -- 'INDEXED', 'FAILED', 'UNAUTHORIZED'
    visual_metadata TEXT, -- JSON blob for images (dimensions, exif, etc.)
    FOREIGN KEY (folder_id) REFERENCES authorized_folders(id) ON DELETE CASCADE
);

-- Table: file_content
CREATE TABLE IF NOT EXISTS file_content (
    file_id INTEGER PRIMARY KEY,
    raw_char_count INTEGER DEFAULT 0,
    searchable_text_preview TEXT,
    redacted_preview TEXT,
    has_ocr INTEGER DEFAULT 0,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- Table: detected_entities
CREATE TABLE IF NOT EXISTS detected_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL,
    entity_text TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    start_char INTEGER,
    end_char INTEGER,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- Table: vector_mappings
CREATE TABLE IF NOT EXISTS vector_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    modality TEXT NOT NULL, -- 'TEXT' or 'IMAGE'
    faiss_vector_id INTEGER NOT NULL,
    vector_dim INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- Table: duplicate_groups
CREATE TABLE IF NOT EXISTS duplicate_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT UNIQUE NOT NULL,
    file_count INTEGER DEFAULT 1,
    total_size INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: version_groups
CREATE TABLE IF NOT EXISTS version_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name TEXT NOT NULL,
    base_file_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (base_file_id) REFERENCES files(id) ON DELETE SET NULL
);

-- Table: version_members
CREATE TABLE IF NOT EXISTS version_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_group_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    similarity_score REAL,
    version_order INTEGER DEFAULT 1,
    FOREIGN KEY (version_group_id) REFERENCES version_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- Indices for rapid querying
CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path);
CREATE INDEX IF NOT EXISTS idx_files_hash ON files(file_hash);
CREATE INDEX IF NOT EXISTS idx_files_tier ON files(privacy_tier);
CREATE INDEX IF NOT EXISTS idx_files_folder ON files(folder_id);
CREATE INDEX IF NOT EXISTS idx_entities_file ON detected_entities(file_id);
CREATE INDEX IF NOT EXISTS idx_vector_mappings_lookup ON vector_mappings(modality, faiss_vector_id);
"""

def init_db(conn: sqlite3.Connection) -> None:
    """Initialize all tables and indices if they do not exist."""
    conn.executescript(CREATE_TABLES_SQL)
    logger.info("Database initialized successfully.")
