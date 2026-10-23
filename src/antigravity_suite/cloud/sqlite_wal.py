"""
SQLite WAL flushing and checkpointing engine.
"""

from __future__ import annotations

import glob
import os
import sqlite3


def checkpoint_single_db(db_path: str) -> bool:
    """Executes PRAGMA wal_checkpoint(TRUNCATE) to flush WAL journal into main db."""
    if not os.path.isfile(db_path):
        return False
    wal_file = f"{db_path}-wal"
    if not os.path.isfile(wal_file) or os.path.getsize(wal_file) == 0:
        return True
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        return True
    except Exception:
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def flush_all_wal(conversations_dir: str) -> int:
    """Flushes WAL on all conversation databases in the directory."""
    if not os.path.isdir(conversations_dir):
        return 0
    count = 0
    for db in glob.glob(os.path.join(conversations_dir, "*.db")):
        if checkpoint_single_db(db):
            count += 1
    return count
