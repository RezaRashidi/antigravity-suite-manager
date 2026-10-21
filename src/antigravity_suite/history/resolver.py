"""Conversation Item Resolution and State Coordination Engine."""
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Set, Tuple
from antigravity_suite.history.audit import get_audit_logger
from antigravity_suite.history.collector import collect_all_conversation_ids, get_db_trajectory_meta, setup_master_directories
from antigravity_suite.history.extractor import extract_conv_prompts, extract_conv_text
from antigravity_suite.history.item_metadata import resolve_item_metadata
from antigravity_suite.history.item_persistence import persist_conversation_item
from antigravity_suite.history.journal import get_sync_journal
from antigravity_suite.history.models import SyncStats
from antigravity_suite.history.projects import get_project_id_for_workspace, normalize_workspace_uri
from antigravity_suite.history.resolver_clean import is_item_clean
from antigravity_suite.history.resolver_heal import heal_workspace_uri
from antigravity_suite.history.title_resolver import resolve_best_title
from antigravity_suite.history.transcript_info import clean_iso_ts, get_transcript_timestamps
from antigravity_suite.proto.cascade import get_last_user_step_index, parse_cascade_summary

__all__ = ["clean_iso_ts", "collect_all_conversation_ids", "get_db_trajectory_meta", "get_transcript_timestamps", "resolve_conversation_item", "setup_master_directories"]


def resolve_conversation_item(
    conv_id: str,
    effective_master: Path,
    master_conv_dir: Path,
    master_brain_dir: Path,
    existing_rows: Dict[str, Tuple],
    all_summaries: Dict[str, bytes],
    cur: sqlite3.Cursor,
    con: sqlite3.Connection,
    stats: SyncStats,
    pinned_set: Optional[Set[str]] = None,
    project_mappings: Optional[Dict[str, str]] = None,
    force_rebuild: bool = False,
    cached_stats: Optional[Dict[str, Tuple[float, int, float, int]]] = None,
) -> None:
    """Evaluates and synchronizes an individual conversation entry in SQLite and Proto index."""
    audit, journal = get_audit_logger(), get_sync_journal()
    db_file = master_conv_dir / f"{conv_id}.db"
    tr_file = master_brain_dir / conv_id / ".system_generated" / "logs" / "transcript.jsonl"
    curr_raw = all_summaries.get(conv_id)
    parsed_raw = parse_cascade_summary(curr_raw) if (curr_raw and pinned_set is not None) else {}

    if is_item_clean(conv_id, db_file, tr_file, existing_rows, all_summaries, pinned_set, parsed_raw, cached_stats=cached_stats, force=force_rebuild):
        return
    if not parsed_raw and curr_raw:
        parsed_raw = parse_cascade_summary(curr_raw)

    meta = resolve_item_metadata(conv_id, effective_master, db_file, master_brain_dir, existing_rows, parsed_raw, pinned_set)
    curr_title = existing_rows[conv_id][0] if conv_id in existing_rows else ""
    curr_prev = existing_rows[conv_id][1] if conv_id in existing_rows else ""
    curr_step_cnt = existing_rows[conv_id][2] if conv_id in existing_rows else parsed_raw.get("step_count", 0)

    ext_t, ext_p = extract_conv_text(db_file, meta["transcript_file"])
    prompt_cands = extract_conv_prompts(db_file, meta["transcript_file"])
    if ext_p:
        prompt_cands.add(ext_p.strip())

    existing_ws = existing_rows[conv_id][7] if conv_id in existing_rows and len(existing_rows[conv_id]) > 7 else None
    existing_proj = existing_rows[conv_id][8] if conv_id in existing_rows and len(existing_rows[conv_id]) > 8 else None
    ws_uri = heal_workspace_uri(normalize_workspace_uri(meta["db_ws_uri"] or parsed_raw.get("workspace_uri") or existing_ws), meta, parsed_raw, existing_proj)

    target_app_data_dir = "antigravity"
    mapped_pid = get_project_id_for_workspace(ws_uri, mappings=project_mappings) if ws_uri else None
    proj_id = mapped_pid if (mapped_pid and mapped_pid != "outside-of-project") else (existing_proj or "")

    final_title, title_source = resolve_best_title(
        existing_candidates=[curr_title, meta["anno_title"], parsed_raw.get("title", "")],
        llm_candidates=[parsed_raw.get("summary", ""), curr_prev],
        clean_artifact_title=ext_t,
        prompt_cands=prompt_cands,
        fallback_workspace=ws_uri,
    )
    final_prev = ext_p or curr_prev or parsed_raw.get("summary", "") or final_title
    if curr_title != final_title:
        audit.log_title_change(conv_id, curr_title, final_title, reason="sync_sanitization", workspace_uri=ws_uri)

    target_step_cnt = max(meta["actual_steps"], curr_step_cnt, 1)
    user_step = get_last_user_step_index(db_file, target_step_cnt)

    persist_conversation_item(
        conv_id, con, all_summaries, db_file, effective_master, final_title, final_prev,
        target_step_cnt, user_step, meta, ws_uri, proj_id, target_app_data_dir
    )

    act = "TITLE_UPDATED" if curr_title != final_title else "SYNCHRONIZED"
    journal.record_chat_action(conv_id=conv_id, action=act, title=final_title, title_source=title_source, old_title=curr_title, partition=target_app_data_dir, partition_reason="unified_history", step_count=target_step_cnt, mutations=["sqlite", "proto", "vscdb", "anno"])

    if cached_stats is not None:
        db_s = db_file.stat() if db_file.is_file() else None
        tr_s = tr_file.stat() if tr_file.is_file() else None
        cached_stats[conv_id] = (db_s.st_mtime if db_s else 0.0, db_s.st_size if db_s else 0, tr_s.st_mtime if tr_s else 0.0, tr_s.st_size if tr_s else 0)

    stats.conversations_updated += 1
    stats.dirty_conv_ids.add(conv_id)
