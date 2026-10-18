"""
Safe SQLite database copying and step count utilities for history sync.
"""

from __future__ import annotations

import os
import shutil
import sqlite3


def get_db_step_count(db_path: str) -> int:
    if not os.path.isfile(db_path):
        return -1
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as con:
            row = con.execute("SELECT count(*) FROM steps").fetchone()
            return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return -1


def copy_sqlite_db_safely(src_db: str, dst_db: str) -> None:
    shutil.copy2(src_db, dst_db)
    for ext in ["-wal", "-shm"]:
        s_side = f"{src_db}{ext}"
        d_side = f"{dst_db}{ext}"
        if os.path.exists(s_side):
            shutil.copy2(s_side, d_side)
        elif os.path.exists(d_side):
            try:
                os.remove(d_side)
            except Exception:
                pass


__all__ = ["get_db_step_count", "copy_sqlite_db_safely"]
