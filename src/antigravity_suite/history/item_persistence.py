"""
Conversation Item Persistence and Store Synchronization.

Saves conversation state to SQLite, Protobuf cache, annotation files,
and conversation trajectory metadata blobs.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

from antigravity_suite.history.checkpoint_sync import ensure_db_checkpoint_title
from antigravity_suite.history.extractor import sync_annotation_file
from antigravity_suite.history.models import ConversationSummary
from antigravity_suite.history.sqlite_store import upsert_summary
from antigravity_suite.history.title_sanitizer import is_clean_title
from antigravity_suite.proto.cascade import build_cascade_summary
from antigravity_suite.proto.trajectory import build_trajectory_metadata_blob


def persist_conversation_item(
    conv_id: str,
    con: sqlite3.Connection,
    all_summaries: Dict[str, bytes],
    db_file: Path,
    effective_master: Path,
    final_title: str,
    final_prev: str,
    target_step_cnt: int,
    user_step: int,
    meta: Dict[str, Any],
    ws_uri: str,
    proj_id: str,
    target_app_data_dir: str,
) -> bytes:
    """Builds authentic Protobuf summary and persists to SQLite and companion stores."""
    proto_summary = final_title if (is_clean_title(final_title) and final_title != "Conversation") else "---"
    raw_to_store = build_cascade_summary(
        conv_id,
        final_title,
        proto_summary,
        target_step_cnt,
        last_modified_iso=meta["final_modified_iso"],
        last_user_step=user_step,
        workspace_uri=ws_uri,
        project_id=proj_id,
        created_iso=meta["final_created_iso"],
        last_user_input_iso=meta["final_user_input_iso"],
        pinned=meta["is_pinned"],
        archived=meta["is_archived"],
    )
    all_summaries[conv_id] = raw_to_store

    ws_str = ""
    if ws_uri:
        ws_str = str(ws_uri) if str(ws_uri).startswith("[") else json.dumps([str(ws_uri)])
    model = ConversationSummary(
        conversation_id=conv_id,
        title=final_title,
        preview=final_prev,
        step_count=target_step_cnt,
        last_modified_time=meta["final_modified_iso"],
        last_user_input_time=meta["final_user_input_iso"],
        last_user_input_step_index=user_step,
        raw_summary=raw_to_store,
        workspace_uris=ws_str,
        project_id=proj_id or "",
        source="",
        app_data_dir=target_app_data_dir,
    )
    upsert_summary(con, model)

    is_fb_title = final_title.endswith(" Chat") or final_title.startswith("Desktop:") or final_title in ["Conversation", "Untitled Conversation"]
    if final_title and is_clean_title(final_title) and not is_fb_title:
        sync_annotation_file(effective_master, conv_id, final_title, pinned=meta["is_pinned"], archived=meta["is_archived"], force=True)
    elif meta["is_pinned"] or meta["is_archived"]:
        sync_annotation_file(effective_master, conv_id, "", pinned=meta["is_pinned"], archived=meta["is_archived"], force=False)

    if meta["has_db"] and ws_uri:
        try:
            if final_title and not final_title.endswith(" Chat") and final_title not in ["Conversation", "Untitled Conversation"]:
                ensure_db_checkpoint_title(db_file, conv_id, final_title, prompt=final_prev)
            blob = build_trajectory_metadata_blob(conv_id=conv_id, workspace_uri=ws_uri, project_id=proj_id)
            with sqlite3.connect(str(db_file), timeout=15.0) as target_db:
                target_db.execute("CREATE TABLE IF NOT EXISTS trajectory_metadata_blob (id TEXT PRIMARY KEY DEFAULT 'main', data BLOB);")
                row = target_db.execute("SELECT data FROM trajectory_metadata_blob WHERE id = 'main';").fetchone()
                if not row or row[0] != blob:
                    target_db.execute("INSERT OR REPLACE INTO trajectory_metadata_blob (id, data) VALUES ('main', ?);", (blob,))
                    target_db.commit()
        except Exception:
            pass

    return raw_to_store
