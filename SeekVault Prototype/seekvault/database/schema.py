import sqlite3
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Increment this whenever the schema changes.  The migration runner in
# `init_db()` compares CURRENT_SCHEMA_VERSION against the value stored in the
# `db_meta` table and applies any pending migrations in order.
CURRENT_SCHEMA_VERSION = 4

# ──────────────────────────────────────────────────────────────────────────────
# Baseline CREATE statements (version 1)
# ──────────────────────────────────────────────────────────────────────────────
_CREATE_V1 = """
-- Schema version tracking (always created first)
CREATE TABLE IF NOT EXISTS db_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Table: authorized_folders
CREATE TABLE IF NOT EXISTS authorized_folders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path  TEXT UNIQUE NOT NULL,
    is_recursive INTEGER DEFAULT 1,
    is_active    INTEGER DEFAULT 1,
    added_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: files
CREATE TABLE IF NOT EXISTS files (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id        INTEGER,
    file_path        TEXT UNIQUE NOT NULL,
    file_name        TEXT NOT NULL,
    file_extension   TEXT NOT NULL,
    file_size        INTEGER NOT NULL,
    file_hash        TEXT NOT NULL,
    file_type        TEXT NOT NULL,        -- 'DOCUMENT' | 'IMAGE'
    modified_at      TIMESTAMP NOT NULL,
    indexed_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    privacy_tier     TEXT NOT NULL DEFAULT 'FULL',    -- 'FULL' | 'REDACTED' | 'METADATA_ONLY'
    status           TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING' | 'INDEXED' | 'FAILED' | 'UNAUTHORIZED'
    error_detail     TEXT,                -- populated when status = 'FAILED'
    visual_metadata  TEXT,               -- JSON blob for images
    FOREIGN KEY (folder_id) REFERENCES authorized_folders(id) ON DELETE CASCADE
);

-- Table: file_content
CREATE TABLE IF NOT EXISTS file_content (
    file_id               INTEGER PRIMARY KEY,
    raw_char_count        INTEGER DEFAULT 0,
    searchable_text_preview TEXT,
    redacted_preview      TEXT,
    has_ocr               INTEGER DEFAULT 0,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- Table: detected_entities  (entity_text is NEVER stored raw — use a masked token)
CREATE TABLE IF NOT EXISTS detected_entities (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id      INTEGER NOT NULL,
    entity_type  TEXT NOT NULL,
    entity_token TEXT NOT NULL,  -- masked token e.g. <EMAIL_REDACTED_a3f2> (raw PII never stored)
    confidence   REAL DEFAULT 1.0,
    detected_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- Table: vector_mappings
CREATE TABLE IF NOT EXISTS vector_mappings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id         INTEGER NOT NULL,
    modality        TEXT NOT NULL,      -- 'TEXT' | 'IMAGE'
    faiss_vector_id INTEGER NOT NULL,
    vector_dim      INTEGER NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- Table: duplicate_groups
CREATE TABLE IF NOT EXISTS duplicate_groups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash  TEXT UNIQUE NOT NULL,
    file_count INTEGER DEFAULT 1,
    total_size INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: version_groups
CREATE TABLE IF NOT EXISTS version_groups (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name   TEXT NOT NULL,
    base_file_id INTEGER,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (base_file_id) REFERENCES files(id) ON DELETE SET NULL
);

-- Table: version_members
CREATE TABLE IF NOT EXISTS version_members (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    version_group_id INTEGER NOT NULL,
    file_id          INTEGER NOT NULL,
    similarity_score REAL,
    version_order    INTEGER DEFAULT 1,
    is_dismissed     INTEGER DEFAULT 0,  -- user can dismiss incorrect suggestions
    FOREIGN KEY (version_group_id) REFERENCES version_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (file_id)          REFERENCES files(id)          ON DELETE CASCADE
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_files_path          ON files(file_path);
CREATE INDEX IF NOT EXISTS idx_files_hash          ON files(file_hash);
CREATE INDEX IF NOT EXISTS idx_files_tier          ON files(privacy_tier);
CREATE INDEX IF NOT EXISTS idx_files_folder        ON files(folder_id);
CREATE INDEX IF NOT EXISTS idx_files_status        ON files(status);
CREATE INDEX IF NOT EXISTS idx_entities_file       ON detected_entities(file_id);
CREATE INDEX IF NOT EXISTS idx_vector_file_mod     ON vector_mappings(modality, faiss_vector_id);

-- FTS5 full-text virtual table (standalone; stores compressed text in shadow tables)
-- file_id is unindexed so we can join it back to the files table.
CREATE VIRTUAL TABLE IF NOT EXISTS file_content_fts
    USING fts5(
        file_id UNINDEXED,
        searchable_text_preview,
        tokenize='porter ascii'
    );
"""

# ──────────────────────────────────────────────────────────────────────────────
# Migration: v1 → v2
#   • Renames detected_entities.entity_text → entity_token (PII safety fix F-5)
#   • Adds files.error_detail column
#   • Adds version_members.is_dismissed column
# ──────────────────────────────────────────────────────────────────────────────
_MIGRATION_V2 = """
-- Rename entity_text to entity_token and drop position columns (schema v2)
CREATE TABLE IF NOT EXISTS detected_entities_v2 (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id      INTEGER NOT NULL,
    entity_type  TEXT NOT NULL,
    entity_token TEXT NOT NULL,
    confidence   REAL DEFAULT 1.0,
    detected_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

INSERT OR IGNORE INTO detected_entities_v2 (id, file_id, entity_type, entity_token, confidence, detected_at)
    SELECT id, file_id, entity_type,
           COALESCE(entity_text, '<MIGRATED_REDACTED>') AS entity_token,
           confidence,
           detected_at
    FROM detected_entities;

DROP TABLE IF EXISTS detected_entities;

ALTER TABLE detected_entities_v2 RENAME TO detected_entities;

CREATE INDEX IF NOT EXISTS idx_entities_file ON detected_entities(file_id);

-- Add error_detail to files if absent
ALTER TABLE files ADD COLUMN error_detail TEXT;

-- Add is_dismissed to version_members if absent
ALTER TABLE version_members ADD COLUMN is_dismissed INTEGER DEFAULT 0;
"""

# ──────────────────────────────────────────────────────────────────────────────
# Migration: v2 → v3
#   • Creates the FTS5 virtual table file_content_fts if it does not exist.
#   • Rebuilds the index from existing file_content rows.
# ──────────────────────────────────────────────────────────────────────────────
_MIGRATION_V3_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS file_content_fts
    USING fts5(
        file_id UNINDEXED,
        searchable_text_preview,
        tokenize='porter ascii'
    );
"""


def _get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the stored schema version, or 0 if the table doesn't exist yet."""
    try:
        row = conn.execute(
            "SELECT value FROM db_meta WHERE key = 'schema_version'"
        ).fetchone()
        return int(row[0]) if row else 0
    except sqlite3.OperationalError:
        return 0


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        "INSERT INTO db_meta (key, value) VALUES ('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(version),),
    )


def _backup_database(db_path: Path) -> Optional[Path]:
    """Create a timestamped copy of the database before a migration.
    Returns the backup path, or None if the DB doesn't exist yet."""
    if not db_path.exists():
        return None
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"seekvault_pre_migration_v{CURRENT_SCHEMA_VERSION}_{ts}.db")
    shutil.copy2(db_path, backup_path)
    logger.info("Schema migration backup created: %s", backup_path)
    return backup_path


def init_db(conn: sqlite3.Connection, db_path: Optional[Path] = None) -> None:
    """
    Initialize or migrate the database schema safely.

    Strategy:
    - Always runs inside the caller-supplied connection (which wraps a transaction).
    - On a brand-new database, creates all tables at the current version in one
      executescript call, then records schema_version = CURRENT_SCHEMA_VERSION.
    - On an existing database, reads the stored schema_version and applies only
      the pending migrations in order, first backing up the file.
    - Never resets or drops the database automatically during normal startup.
    """
    current_version = _get_schema_version(conn)

    if current_version == 0:
        # Fresh database — create everything at the latest baseline.
        conn.executescript(_CREATE_V1)
        # The baseline already incorporates all v2 changes (entity_token, error_detail,
        # is_dismissed, idx_files_status), so record immediately at CURRENT_SCHEMA_VERSION.
        _set_schema_version(conn, CURRENT_SCHEMA_VERSION)
        logger.info("Database created fresh at schema version %d.", CURRENT_SCHEMA_VERSION)
        return  # nothing to migrate

    # Apply incremental migrations for pre-existing databases
    if current_version < 2:
        if db_path and db_path.exists():
            _backup_database(db_path)
        # ALTER TABLE inside executescript has implicit commit issues; run statements individually
        _apply_migration_v2(conn)
        _set_schema_version(conn, 2)
        logger.info("Migrated database schema from v1 → v2.")
        current_version = 2

    if current_version < 3:
        _apply_migration_v3(conn)
        _set_schema_version(conn, 3)
        logger.info("Migrated database schema from v2 → v3 (FTS5 table).")
        current_version = 3

    if current_version < 4:
        _apply_migration_v4(conn)
        _set_schema_version(conn, 4)
        logger.info("Migrated database schema from v3 → v4 (version dismissal).")
        current_version = 4

    if current_version < CURRENT_SCHEMA_VERSION:
        logger.warning(
            "Schema version %d is older than current %d but no migration found — "
            "verify schema integrity manually.",
            current_version,
            CURRENT_SCHEMA_VERSION,
        )
    else:
        logger.debug("Schema is up to date at version %d.", CURRENT_SCHEMA_VERSION)

    # Defensive self-healing: ensure critical columns exist regardless of recorded version
    file_cols = [row[1] for row in conn.execute("PRAGMA table_info(files)").fetchall()]
    if "error_detail" not in file_cols:
        conn.execute("ALTER TABLE files ADD COLUMN error_detail TEXT")
        logger.info("Self-healing: added missing files.error_detail column.")

    vm_cols = [row[1] for row in conn.execute("PRAGMA table_info(version_members)").fetchall()]
    if "is_dismissed" not in vm_cols:
        conn.execute("ALTER TABLE version_members ADD COLUMN is_dismissed INTEGER DEFAULT 0")
        logger.info("Self-healing: added missing version_members.is_dismissed column.")

    try:
        de_cols = [row[1] for row in conn.execute("PRAGMA table_info(detected_entities)").fetchall()]
        if "entity_text" in de_cols:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _detected_entities_new (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id      INTEGER NOT NULL,
                    entity_type  TEXT NOT NULL,
                    entity_token TEXT NOT NULL,
                    confidence   REAL DEFAULT 1.0,
                    detected_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                INSERT OR IGNORE INTO _detected_entities_new
                    (id, file_id, entity_type, entity_token, confidence, detected_at)
                SELECT id, file_id, entity_type,
                       COALESCE(entity_token, entity_text, '<MIGRATED_REDACTED>'),
                       confidence,
                       detected_at
                FROM detected_entities
            """)
            conn.execute("DROP TABLE detected_entities")
            conn.execute("ALTER TABLE _detected_entities_new RENAME TO detected_entities")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_file ON detected_entities(file_id)")
            logger.info("Self-healing: migrated detected_entities to remove legacy entity_text.")
        elif de_cols and "entity_token" not in de_cols:
            conn.execute("ALTER TABLE detected_entities ADD COLUMN entity_token TEXT")
            logger.info("Self-healing: added missing detected_entities.entity_token column.")
    except Exception as exc:
        logger.warning("Could not verify detected_entities columns: %s", exc)




def _apply_migration_v2(conn: sqlite3.Connection) -> None:
    """
    Migrate detected_entities: rename entity_text → entity_token,
    add files.error_detail, add version_members.is_dismissed.
    SQLite ALTER TABLE is limited, so we use a table-rebuild strategy.
    """
    # Check if entity_text column exists (pre-migration databases)
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(detected_entities)").fetchall()]
    except sqlite3.OperationalError:
        cols = []

    if "entity_text" in cols:
        # Rebuild the table with renamed column
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _detected_entities_new (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id      INTEGER NOT NULL,
                entity_type  TEXT NOT NULL,
                entity_token TEXT NOT NULL,
                confidence   REAL DEFAULT 1.0,
                detected_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO _detected_entities_new
                (id, file_id, entity_type, entity_token, confidence, detected_at)
            SELECT id, file_id, entity_type,
                   COALESCE(entity_text, '<MIGRATED_REDACTED>'),
                   confidence,
                   detected_at
            FROM detected_entities
        """)
        conn.execute("DROP TABLE detected_entities")
        conn.execute("ALTER TABLE _detected_entities_new RENAME TO detected_entities")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_file ON detected_entities(file_id)")
        logger.info("v2 migration: entity_text column renamed to entity_token.")

    # Add error_detail to files if missing
    file_cols = [row[1] for row in conn.execute("PRAGMA table_info(files)").fetchall()]
    if "error_detail" not in file_cols:
        conn.execute("ALTER TABLE files ADD COLUMN error_detail TEXT")
        logger.info("v2 migration: added files.error_detail column.")

    # Add is_dismissed to version_members if missing
    vm_cols = [row[1] for row in conn.execute("PRAGMA table_info(version_members)").fetchall()]
    if "is_dismissed" not in vm_cols:
        conn.execute("ALTER TABLE version_members ADD COLUMN is_dismissed INTEGER DEFAULT 0")
        logger.info("v2 migration: added version_members.is_dismissed column.")

    # Ensure status index exists
    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)")


def _apply_migration_v3(conn: sqlite3.Connection) -> None:
    """
    Create the standalone FTS5 virtual table file_content_fts and backfill
    existing file_content rows.  Safe to call multiple times (IF NOT EXISTS).
    """
    conn.executescript(_MIGRATION_V3_SQL)
    # Backfill any existing file_content rows into the FTS index
    try:
        rows = conn.execute(
            "SELECT file_id, searchable_text_preview FROM file_content "
            "WHERE searchable_text_preview IS NOT NULL AND searchable_text_preview != ''"
        ).fetchall()
        for row in rows:
            conn.execute(
                "INSERT INTO file_content_fts(file_id, searchable_text_preview) VALUES (?, ?)",
                (row[0], row[1])
            )
        logger.info("v3 migration: FTS5 table created; backfilled %d rows.", len(rows))
    except Exception as exc:  # pragma: no cover
        logger.warning("v3 migration: FTS5 backfill skipped — %s", exc)


def _apply_migration_v4(conn: sqlite3.Connection) -> None:
    """
    Add version_members.is_dismissed column if absent.
    """
    try:
        vm_cols = [row[1] for row in conn.execute("PRAGMA table_info(version_members)").fetchall()]
        if "is_dismissed" not in vm_cols:
            conn.execute("ALTER TABLE version_members ADD COLUMN is_dismissed INTEGER DEFAULT 0")
            logger.info("v4 migration: added version_members.is_dismissed column.")
    except Exception as exc:  # pragma: no cover
        logger.warning("v4 migration: error checking or adding is_dismissed — %s", exc)

