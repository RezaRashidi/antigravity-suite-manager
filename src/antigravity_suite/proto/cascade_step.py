"""
Conversation Step Index Query Utilities.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def get_last_user_step_index(db_path: Path, fallback_step_count: int = 0) -> int:
    """Reads the highest index where step_type = 14 (User prompt) from conversation database."""
    if not db_path.is_file():
        return max(0, fallback_step_count - 1)
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=15.0)
        row = conn.cursor().execute("SELECT MAX(idx) FROM steps WHERE step_type = 14;").fetchone()
        if row and row[0] is not None:
            return int(row[0])
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return max(0, fallback_step_count - 1)
