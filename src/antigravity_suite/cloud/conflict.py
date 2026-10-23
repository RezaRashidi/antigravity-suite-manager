"""
Step inspection, fast-forward evaluation, and divergence forking.
"""

from __future__ import annotations

import datetime
import os
import shutil
import sqlite3
from typing import Tuple


def get_db_metrics(db_path: str) -> Tuple[int, int, float]:
    """Returns (max_step_idx, total_steps, mtime) for a conversation db."""
    if not os.path.isfile(db_path):
        return -1, 0, 0.0
    mtime = os.path.getmtime(db_path)
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        row = conn.cursor().execute("SELECT MAX(idx), COUNT(*) FROM steps;").fetchone()
        if row and row[0] is not None:
            return int(row[0]), int(row[1]), mtime
        return -1, 0, mtime
    except Exception:
        return -1, 0, mtime
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


def evaluate_sync_action(local_db: str, incoming_db: str) -> Tuple[bool, str]:
    """
    Evaluates whether incoming db should overwrite local db.
    Returns (should_apply, reason_tag).
    """
    if not os.path.isfile(local_db):
        return True, "new"

    l_max, l_cnt, l_mtime = get_db_metrics(local_db)
    i_max, i_cnt, i_mtime = get_db_metrics(incoming_db)

    if i_max > l_max or i_cnt > l_cnt:
        return True, "fast_forward"
    if i_max < l_max or i_cnt < l_cnt:
        return False, "local_ahead"
    if i_mtime > l_mtime + 2.0:
        return True, "newer_timestamp"
    return False, "identical"


def fork_local_divergence(local_db: str, brain_base_dir: str = "") -> str:
    """Creates a safety fork of local conversation db and brain artifacts before overwriting."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = os.path.splitext(local_db)[0]
    forked_db = f"{stem}_fork_{ts}.db"
    shutil.copy2(local_db, forked_db)

    cid = os.path.splitext(os.path.basename(local_db))[0]
    if brain_base_dir:
        src_b = os.path.join(brain_base_dir, cid)
        if os.path.isdir(src_b):
            dst_b = os.path.join(brain_base_dir, f"{cid}_fork_{ts}")
            shutil.copytree(src_b, dst_b, dirs_exist_ok=True)
    return forked_db
