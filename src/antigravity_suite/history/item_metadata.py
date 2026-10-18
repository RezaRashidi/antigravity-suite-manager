"""
Conversation Item Metadata and Timestamp Resolver.

Extracts timestamps, actual steps, trajectory metadata, and UI flags (pinned, archived).
"""

from __future__ import annotations

import datetime
import time
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from antigravity_suite.history.collector import get_db_trajectory_meta
from antigravity_suite.history.sqlite_store import get_actual_steps_count
from antigravity_suite.history.transcript_info import clean_iso_ts, get_transcript_timestamps
from antigravity_suite.history.extractor import get_annotation_info


def resolve_item_metadata(
    conv_id: str,
    effective_master: Path,
    db_file: Path,
    master_brain_dir: Path,
    existing_rows: Dict[str, Tuple],
    parsed_raw: Dict[str, Any],
    pinned_set: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Resolves and validates timestamps, step counts, and flags for a conversation."""
    has_db = db_file.is_file() and db_file.stat().st_size > 0
    file_mtime = db_file.stat().st_mtime if has_db else time.time()
    file_mtime_iso = datetime.datetime.fromtimestamp(file_mtime, tz=datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S.000000+00:00"
    )
    actual_steps = get_actual_steps_count(db_file) if has_db else (
        existing_rows[conv_id][2] if conv_id in existing_rows else 0
    )

    transcript_file = master_brain_dir / conv_id / ".system_generated" / "logs" / "transcript.jsonl"
    t_created, t_user_input, t_modified = get_transcript_timestamps(transcript_file)

    sql_mtime = clean_iso_ts(existing_rows[conv_id][3]) if conv_id in existing_rows and existing_rows[conv_id][3] else None
    sql_user_input = (
        clean_iso_ts(existing_rows[conv_id][5])
        if conv_id in existing_rows and len(existing_rows[conv_id]) > 5 and existing_rows[conv_id][5]
        else None
    )

    t_clean_created = clean_iso_ts(t_created)
    t_clean_user_input = clean_iso_ts(t_user_input)
    t_clean_modified = clean_iso_ts(t_modified)

    parsed_modified = clean_iso_ts(parsed_raw.get("last_modified_iso"))
    parsed_user_input = clean_iso_ts(parsed_raw.get("last_user_input_iso"))
    parsed_created = clean_iso_ts(parsed_raw.get("created_iso"))

    final_modified_iso = t_clean_modified or parsed_modified or sql_mtime or file_mtime_iso
    final_user_input_iso = t_clean_user_input or parsed_user_input or sql_user_input or final_modified_iso
    final_created_iso = t_clean_created or parsed_created or final_user_input_iso or final_modified_iso

    anno_info = get_annotation_info(effective_master, conv_id)
    raw_pinned = bool(parsed_raw.get("pinned", False))
    raw_arc = bool(parsed_raw.get("archived", False))

    if pinned_set is not None and conv_id in pinned_set:
        is_pinned = True
    elif anno_info.get("exists") and anno_info.get("pinned") is not None:
        is_pinned = bool(anno_info.get("pinned"))
    else:
        is_pinned = raw_pinned

    is_archived = bool(anno_info.get("archived")) if anno_info.get("exists") and anno_info.get("archived") is not None else raw_arc
    db_ws_uri, db_proj_id = get_db_trajectory_meta(db_file) if has_db else (None, None)

    return {
        "has_db": has_db,
        "actual_steps": actual_steps,
        "final_modified_iso": final_modified_iso,
        "final_user_input_iso": final_user_input_iso,
        "final_created_iso": final_created_iso,
        "anno_title": anno_info.get("title"),
        "is_pinned": is_pinned,
        "is_archived": is_archived,
        "db_ws_uri": db_ws_uri,
        "db_proj_id": db_proj_id,
        "transcript_file": transcript_file,
    }
