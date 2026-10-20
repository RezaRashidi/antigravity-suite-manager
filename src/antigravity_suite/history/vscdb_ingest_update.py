"""
Updating Existing Conversation Summaries from IDE state.vscdb.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Optional, Set

from antigravity_suite.history.extractor import is_clean_title, is_prompt_text, sync_annotation_file
from antigravity_suite.history.projects import get_project_id_for_workspace, normalize_workspace_uri
from antigravity_suite.history.sqlite_store import get_actual_steps_count
from antigravity_suite.history.vscdb_meta import get_db_trajectory_meta
from antigravity_suite.proto.cascade import build_cascade_summary, get_last_user_step_index


def update_existing_from_ide(
    u_id: str,
    ide_title: str,
    curr_t: str,
    curr_parsed: dict,
    conv_prompts: Optional[Set[str]],
    all_summaries: Dict[str, bytes],
    db_p: Path,
    cur: sqlite3.Cursor,
    master_conv_dir: Path,
    pinned_set: Optional[Set[str]] = None,
) -> bool:
    """Updates an existing conversation summary if IDE has an authentic title."""
    is_fb = curr_t in ["Conversation", "Untitled Conversation"] or curr_t.endswith(" Chat")
    if not (ide_title and (not curr_t or not is_clean_title(curr_t) or is_prompt_text(curr_t, conv_prompts) or is_fb)):
        return False

    db_ws_uri, db_proj_id = get_db_trajectory_meta(db_p)
    raw_ws = db_ws_uri or curr_parsed.get("workspace_uri")
    norm_ws = normalize_workspace_uri(raw_ws)
    mapped_pid = get_project_id_for_workspace(norm_ws) if norm_ws else None
    clean_mapped = mapped_pid if mapped_pid and mapped_pid != "outside-of-project" else ""
    clean_curr = curr_parsed.get("project_id") if curr_parsed.get("project_id") and curr_parsed.get("project_id") != "outside-of-project" else ""
    clean_db = db_proj_id if db_proj_id and db_proj_id != "outside-of-project" else ""

    existing_sql_pid = ""
    try:
        sql_row = cur.execute("SELECT project_id FROM conversation_summaries WHERE conversation_id = ?;", (u_id,)).fetchone()
        if sql_row and sql_row[0] and sql_row[0] != "outside-of-project":
            existing_sql_pid = sql_row[0]
    except Exception:
        pass

    effective_pid = clean_mapped or existing_sql_pid or clean_db or clean_curr or ""
    sc = max(get_actual_steps_count(db_p), curr_parsed.get("step_count", 0), curr_parsed.get(2, 0), 1)
    user_step = get_last_user_step_index(db_p, sc)
    is_pin = bool((pinned_set and u_id in pinned_set) or curr_parsed.get("pinned", False))
    is_arc = bool(curr_parsed.get("archived", False))

    new_bin = build_cascade_summary(
        u_id, ide_title, ide_title, sc,
        last_modified_iso=curr_parsed.get("last_modified_iso") or curr_parsed.get("ts_3"),
        last_user_step=user_step, workspace_uri=norm_ws, project_id=effective_pid,
        created_iso=curr_parsed.get("created_iso") or curr_parsed.get("ts_7"),
        last_user_input_iso=curr_parsed.get("last_user_input_iso") or curr_parsed.get("ts_10"),
        pinned=is_pin, archived=is_arc,
    )
    all_summaries[u_id] = new_bin
    cur.execute("UPDATE conversation_summaries SET title=?, raw_summary=? WHERE conversation_id=?", (ide_title, new_bin, u_id))
    sync_annotation_file(master_conv_dir.parent, u_id, ide_title, pinned=is_pin, archived=is_arc, force=True)
    from antigravity_suite.history.checkpoint_sync import ensure_db_checkpoint_title
    ensure_db_checkpoint_title(db_p, u_id, ide_title)
    return True
