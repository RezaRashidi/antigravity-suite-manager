"""
Annotation Files Synchronization Engine.

Manages annotations/<conv_id>.pbtxt files for Desktop App UI rendering.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional, Set

from antigravity_suite.history.extractor import sync_annotation_file
from antigravity_suite.history.title_sanitizer import is_clean_title
from antigravity_suite.proto.cascade import parse_cascade_summary


def sync_annotation_files(
    effective_master: Path,
    cur: sqlite3.Cursor,
    pinned_set: Optional[Set[str]] = None,
    target_conv_ids: Optional[Set[str]] = None,
) -> None:
    """Synchronizes annotations/<conv_id>.pbtxt files for Desktop App UI rendering."""
    if pinned_set is None:
        pinned_set = set()
    if target_conv_ids is not None and not target_conv_ids:
        return

    if target_conv_ids is not None:
        placeholders = ",".join("?" for _ in target_conv_ids)
        query = f"SELECT conversation_id, title, raw_summary FROM conversation_summaries WHERE length(title) > 0 AND conversation_id IN ({placeholders});"
        rows = cur.execute(query, list(target_conv_ids)).fetchall()
    else:
        query = "SELECT conversation_id, title, raw_summary FROM conversation_summaries WHERE length(title) > 0;"
        rows = cur.execute(query).fetchall()

    for c_id, c_title, raw_summary in rows:
        is_pin = c_id in pinned_set
        is_arc = False
        if raw_summary:
            try:
                parsed = parse_cascade_summary(raw_summary)
                is_arc = bool(parsed.get("archived", False))
            except Exception:
                pass
        if is_clean_title(c_title):
            sync_annotation_file(effective_master, c_id, c_title, pinned=is_pin, archived=is_arc, force=True)
        elif is_pin or is_arc:
            sync_annotation_file(effective_master, c_id, "Conversation", pinned=is_pin, archived=is_arc, force=False)
        else:
            a_file = os.path.join(str(effective_master), "annotations", f"{c_id}.pbtxt")
            if os.path.isfile(a_file):
                try:
                    os.remove(a_file)
                except Exception:
                    pass
