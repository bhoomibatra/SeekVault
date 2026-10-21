import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from seekvault.config import DB_PATH

@contextmanager
def get_db_connection(db_path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional scope around a series of operations."""
    conn = sqlite3.connect(str(db_path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
