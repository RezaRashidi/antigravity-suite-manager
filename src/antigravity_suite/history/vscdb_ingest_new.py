"""
Ingesting New Conversation Summaries from IDE state.vscdb.
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Set

from antigravity_suite.history.extractor import sync_annotation_file
from antigravity_suite.history.models import ConversationSummary
from antigravity_suite.history.projects import get_project_id_for_workspace, normalize_workspace_uri
from antigravity_suite.history.sqlite_store import get_actual_steps_count, upsert_summary
from antigravity_suite.history.vscdb_meta import get_db_trajectory_meta
from antigravity_suite.proto.cascade import build_cascade_summary, get_last_user_step_index


def insert_new_from_ide(
    u_id: str,
    title_to_use: str,
    parsed: dict,
    all_summaries: Dict[str, bytes],
    db_p: Path,
    con: sqlite3.Connection,
    master_conv_dir: Path,
    pinned_set: Optional[Set[str]] = None,
) -> None:
    """Inserts a new conversation found in IDE state.vscdb into SQLite summaries and annotations."""
    db_ws_uri, db_proj_id = get_db_trajectory_meta(db_p)
    raw_ws = db_ws_uri or parsed.get("workspace_uri")
    norm_ws = normalize_workspace_uri(raw_ws)
    mapped_pid = get_project_id_for_workspace(norm_ws) if norm_ws else None
    clean_mapped = mapped_pid if mapped_pid and mapped_pid != "outside-of-project" else ""
    clean_parsed = parsed.get("project_id") if parsed.get("project_id") and parsed.get("project_id") != "outside-of-project" else ""
    clean_db = db_proj_id if db_proj_id and db_proj_id != "outside-of-project" else ""
    effective_pid = clean_mapped or clean_db or clean_parsed or ""

    sc = max(get_actual_steps_count(db_p), parsed.get("step_count", 0), parsed.get(2, 0), 1)
    user_step = get_last_user_step_index(db_p, sc)
    is_pin = bool((pinned_set and u_id in pinned_set) or parsed.get("pinned", False))
    is_arc = bool(parsed.get("archived", False))

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    last_mod_iso = parsed.get("last_modified_iso") or parsed.get("ts_3") or now_iso
    created_iso = parsed.get("created_iso") or parsed.get("ts_7") or last_mod_iso
    last_user_input_iso = parsed.get("last_user_input_iso") or parsed.get("ts_10") or last_mod_iso

    new_bin = build_cascade_summary(
        u_id, title_to_use, title_to_use, sc,
        last_modified_iso=last_mod_iso, last_user_step=user_step,
        workspace_uri=norm_ws, project_id=effective_pid,
        created_iso=created_iso, last_user_input_iso=last_user_input_iso,
        pinned=is_pin, archived=is_arc,
    )
    all_summaries[u_id] = new_bin

    ws_str = str(norm_ws) if (norm_ws and str(norm_ws).startswith("[")) else (json.dumps([str(norm_ws)]) if norm_ws else "")
    model = ConversationSummary(
        conversation_id=u_id, title=title_to_use, preview=title_to_use, step_count=sc,
        last_modified_time=last_mod_iso.replace("T", " ").replace("Z", "+00:00"),
        last_user_input_time=last_user_input_iso.replace("T", " ").replace("Z", "+00:00"),
        last_user_input_step_index=user_step, raw_summary=new_bin,
        workspace_uris=ws_str, project_id=effective_pid or "", source="", app_data_dir="antigravity",
    )
    upsert_summary(con, model)
    is_fb_t = title_to_use.endswith(" Chat") or title_to_use.startswith("Desktop:") or title_to_use in ["Conversation", "Untitled Conversation"]
    if title_to_use and not is_fb_t:
        sync_annotation_file(master_conv_dir.parent, u_id, title_to_use, pinned=is_pin, archived=is_arc, force=True)
        from antigravity_suite.history.checkpoint_sync import ensure_db_checkpoint_title
        ensure_db_checkpoint_title(db_p, u_id, title_to_use)
    elif is_pin or is_arc:
        sync_annotation_file(master_conv_dir.parent, u_id, "", pinned=is_pin, archived=is_arc, force=False)
