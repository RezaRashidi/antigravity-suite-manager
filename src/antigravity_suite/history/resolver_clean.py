"""
Fast Incremental Dirty-Checking for Conversation Item Resolution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple


def is_item_clean(
    conv_id: str,
    db_file: Path,
    transcript_file: Path,
    existing_rows: Dict[str, Tuple],
    all_summaries: Dict[str, bytes],
    pinned_set: Optional[Set[str]],
    parsed_raw: Dict[str, Any],
    cached_stats: Optional[Dict[str, Tuple[float, int, float, int]]] = None,
    force: bool = False,
) -> bool:
    """Returns True if conversation is already indexed, valid, and untouched on disk."""
    if force or conv_id not in existing_rows:
        return False
    row = existing_rows[conv_id]
    title, step_count = row[0], row[2]
    if not title or "@[" in title:
        return False
    if not step_count or step_count <= 0:
        return False
    lmod = str(row[3]) if len(row) > 3 and row[3] else ""
    if "2026-10-20 22:5" in lmod:
        return False
    raw = all_summaries.get(conv_id) or row[4]
    if not raw or len(raw) <= 20:
        return False
    if conv_id not in all_summaries:
        all_summaries[conv_id] = raw

    if pinned_set is not None:
        is_pinned_wanted = conv_id in pinned_set
        is_pinned_curr = bool(parsed_raw.get("pinned", False))
        if is_pinned_wanted != is_pinned_curr:
            return False

    if cached_stats and conv_id in cached_stats:
        c_db_mtime, c_db_size, c_tr_mtime, c_tr_size = cached_stats[conv_id]
        cur_db_mtime, cur_db_size = (db_file.stat().st_mtime, db_file.stat().st_size) if db_file.is_file() else (0.0, 0)
        cur_tr_mtime, cur_tr_size = (transcript_file.stat().st_mtime, transcript_file.stat().st_size) if transcript_file.is_file() else (0.0, 0)
        if (c_db_mtime == cur_db_mtime and c_db_size == cur_db_size
                and c_tr_mtime == cur_tr_mtime and c_tr_size == cur_tr_size):
            return True

    return False
