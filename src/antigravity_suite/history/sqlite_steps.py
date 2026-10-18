"""
SQLite Step Count Caching and Summaries Ingestion.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from antigravity_suite.history.sqlite_schema import ensure_summaries_schema

_STEP_COUNT_CACHE: Dict[str, Tuple[float, int, int]] = {}


def clear_step_count_cache() -> None:
    """Clears the in-memory step count cache."""
    _STEP_COUNT_CACHE.clear()


def get_actual_steps_count(db_path: Union[str, Path]) -> int:
    """Returns actual step count from trajectory database using compound stat caching."""
    db_str = str(db_path)
    try:
        st = os.stat(db_str)
    except Exception:
        return 0
    mtime, size = st.st_mtime, st.st_size
    if size == 0:
        return 0

    cached = _STEP_COUNT_CACHE.get(db_str)
    if cached is not None and cached[0] == mtime and cached[1] == size:
        return cached[2]

    conn = None
    try:
        conn = sqlite3.connect(db_str, timeout=15.0)
        row = conn.cursor().execute("SELECT count(*), min(idx), max(idx) FROM steps;").fetchone()
        cnt = row[0] if row else 0
        min_idx = row[1] if row and row[1] is not None else 0
        max_idx = row[2] if row and row[2] is not None else -1
        span = max(0, max_idx + 1) if min_idx == 0 else max(0, max_idx - min_idx + 1)
        actual_cnt = max(cnt, span)
        _STEP_COUNT_CACHE[db_str] = (mtime, size, actual_cnt)
        return actual_cnt
    except Exception:
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def load_existing_summaries(db_path: Union[str, Path]) -> Dict[str, Tuple[Any, ...]]:
    """Loads existing indexed summaries from conversation_summaries.db."""
    db_str = str(db_path)
    if not os.path.isfile(db_str):
        return {}
    conn = None
    try:
        conn = sqlite3.connect(db_str, timeout=15.0)
        ensure_summaries_schema(conn)
        existing: Dict[str, Tuple[Any, ...]] = {}
        for r in conn.cursor().execute(
            "SELECT conversation_id, title, preview, step_count, last_modified_time, raw_summary, last_user_input_time, last_user_input_step_index, workspace_uris, project_id FROM conversation_summaries;"
        ).fetchall():
            existing[r[0]] = (r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9])
        return existing
    except Exception:
        return {}
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
