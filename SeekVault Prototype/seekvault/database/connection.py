import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional


@contextmanager
def get_db_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional scope around a series of database operations.

    db_path is resolved lazily (not at module import time) so that the
    SEEKVAULT_DATA_DIR environment variable can be set before the first
    connection is opened.
    """
    if db_path is None:
        # Defer import so env var override in config.py is already applied.
        from seekvault.config import DB_PATH
        db_path = DB_PATH

    conn = sqlite3.connect(str(db_path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")   # write-ahead log for concurrent readers
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
