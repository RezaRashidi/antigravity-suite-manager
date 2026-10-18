"""
Unified History Synchronization and Merge Engine for Antigravity Suite.

Orchestrates multi-profile synchronization across Desktop App, IDE instances,
SQLite indexes, Protobuf binary indexes, and VS Code global storage state.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import re
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

from antigravity_suite.auth.token import refresh_ide_oauth_token
from antigravity_suite.config import DEFAULT_CONFIG, SuiteConfig, get_user_home
from antigravity_suite.history.backup import HistoryBackupManager
from antigravity_suite.history.deletion import (
    detect_and_sync_deletions,
    get_tombstones,
    load_manifest,
)
from antigravity_suite.history.discovery import (
    discover_all_history_sources,
    discover_pinned_conversation_ids,
    replicate_pinned_conversations_order,
)
from antigravity_suite.history.distribution import replicate_to_ide_profiles
from antigravity_suite.history.extractor import (
    extract_conv_prompts,
    extract_conv_text,
    get_annotation_info,
    get_annotation_title,
    is_clean_title,
    is_prompt_text,
    sync_annotation_file,
)
from antigravity_suite.history.models import ConversationSummary, SyncStats
from antigravity_suite.history.pool_merger import merge_brain_folders, merge_raw_db_pools
from antigravity_suite.history.reconstruction import reconstruct_missing_databases
from antigravity_suite.history.sqlite_store import (
    ensure_summaries_schema,
    get_actual_steps_count,
    load_existing_summaries,
    upsert_summary,
)
from antigravity_suite.history.projects import (
    KNOWN_PROJECT_MAPPINGS,
    KNOWN_ROOTS,
    discover_project_mappings,
    ensure_project_configs,
    get_project_id_for_workspace,
    normalize_workspace_uri,
)
from antigravity_suite.history.vscdb_sync import (
    discover_candidate_vscdbs,
    get_db_trajectory_meta,
    ingest_vscdb_summaries,
    write_vscdb_unified_state,
)
from antigravity_suite.proto.cascade import (
    build_cascade_summary,
    get_last_user_step_index,
    parse_cascade_summary,
)
from antigravity_suite.proto.trajectory import build_trajectory_metadata_blob
from antigravity_suite.proto.wire import (
    encode_tag_bytes,
    extract_entries_from_proto,
    extract_pure_binary_summary,
)

# Re-export get_db_trajectory_meta and project helpers for backward compatibility
__all__ = [
    "ensure_project_configs",
    "get_db_trajectory_meta",
    "get_project_id_for_workspace",
    "get_transcript_timestamps",
    "merge_histories",
    "normalize_workspace_uri",
    "setup_master_directories",
    "collect_all_conversation_ids",
    "synchronize_master_summaries",
    "serialize_master_proto",
    "sync_annotation_files",
]


def get_transcript_timestamps(
    transcript_path: Path,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extracts authentic ISO timestamps from transcript.jsonl:
    (created_time, last_user_input_time, last_modified_time)
    Uses streaming and tail-seeking to avoid loading massive multi-megabyte JSONL files into memory.
    """
    if not transcript_path.is_file():
        return None, None, None
    try:
        fsize = transcript_path.stat().st_size
        if fsize == 0:
            return None, None, None

        created_time = None
        last_modified_time = None
        last_user_input_time = None

        with open(transcript_path, "rb") as f:
            # 1. Read first line for created_time
            first_line = f.readline().decode("utf-8", errors="ignore").strip()
            if first_line:
                try:
                    first_obj = json.loads(first_line)
                    created_time = first_obj.get("created_at")
                except Exception:
                    pass

            # 2. Tail-seek for last_modified_time and last_user_input_time
            chunk_size = min(fsize, 65536)
            f.seek(fsize - chunk_size)
            tail_bytes = f.read(chunk_size)
            tail_lines = tail_bytes.decode("utf-8", errors="ignore").splitlines()

            # Discard first line if seek landed in the middle of a line
            if fsize > chunk_size and tail_lines:
                tail_lines.pop(0)

            clean_lines = [l.strip() for l in tail_lines if l.strip()]
            if clean_lines:
                try:
                    last_obj = json.loads(clean_lines[-1])
                    last_modified_time = last_obj.get("created_at")
                except Exception:
                    pass

                for line in reversed(clean_lines):
                    try:
                        obj = json.loads(line)
                        if obj.get("type") == "USER_INPUT":
                            last_user_input_time = obj.get("created_at")
                            break
                    except Exception:
                        continue

            # If last_user_input_time wasn't found in the last 64KB and file is larger,
            # inspect up to the last 256KB before giving up
            if not last_user_input_time and fsize > chunk_size:
                larger_chunk = min(fsize, 262144)
                f.seek(fsize - larger_chunk)
                t_bytes = f.read(larger_chunk)
                t_lines = t_bytes.decode("utf-8", errors="ignore").splitlines()
                if fsize > larger_chunk and t_lines:
                    t_lines.pop(0)
                for line in reversed(t_lines):
                    line_s = line.strip()
                    if not line_s or "USER_INPUT" not in line_s:
                        continue
                    try:
                        obj = json.loads(line_s)
                        if obj.get("type") == "USER_INPUT":
                            last_user_input_time = obj.get("created_at")
                            break
                    except Exception:
                        continue

        return created_time, last_user_input_time, last_modified_time
    except Exception:
        return None, None, None


def _clean_iso_ts(ts_val: Any) -> Optional[str]:
    """Validates and formats an ISO timestamp string. Rejects timestamps <= 1000000000 or year 1."""
    if not ts_val:
        return None
    try:
        s_str = str(ts_val).strip()
        clean = s_str.replace("Z", "+00:00")
        clean = re.sub(r"(\.\d{6})\d+", r"\1", clean)
        dt = datetime.datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        if dt.timestamp() <= 1000000000:
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
    except Exception:
        return None


def setup_master_directories(effective_master: Path) -> Tuple[Path, Path, Path, Path, Path]:
    """
    Creates and configures canonical directory paths and maintains symlinks for SQLite DB.
    Returns:
        (master_conv_dir, master_brain_dir, master_sum_db, master_proto, master_anno)
    """
    master_conv_dir = effective_master / "conversations"
    master_brain_dir = effective_master / "brain"
    master_sum_db = effective_master / "conversation_summaries.db"
    sub_sum_db = master_conv_dir / "conversation_summaries.db"
    master_proto = effective_master / "agyhub_summaries_proto.pb"
    master_anno = effective_master / "annotations"

    master_conv_dir.mkdir(parents=True, exist_ok=True)
    master_brain_dir.mkdir(parents=True, exist_ok=True)
    master_anno.mkdir(parents=True, exist_ok=True)

    # Ensure master_conv_dir / conversation_summaries.db never exists (prevents Go language server version crash)
    if sub_sum_db.exists() or sub_sum_db.is_symlink():
        if not master_sum_db.exists() and not sub_sum_db.is_symlink():
            try:
                shutil.move(str(sub_sum_db), str(master_sum_db))
            except Exception:
                pass
        else:
            try:
                if sub_sum_db.is_symlink() or sub_sum_db.is_file():
                    os.remove(str(sub_sum_db))
            except Exception:
                pass

    return master_conv_dir, master_brain_dir, master_sum_db, master_proto, master_anno


def collect_all_conversation_ids(
    master_conv_dir: Path,
    existing_rows: Dict[str, Tuple],
    extra_ids: Optional[Iterable[str]] = None,
    tombstones: Optional[Set[str]] = None,
) -> Set[str]:
    """Scans databases, protobufs, in-memory protobuf entries, and existing table rows for 36-char UUIDs, skipping tombstones."""
    all_conv_ids: Set[str] = set()
    uuid_pattern = re.compile(r"^[0-9a-fA-F-]{36}$")

    for db_f in glob.glob(os.path.join(str(master_conv_dir), "*.db")):
        cid = os.path.basename(db_f)[:-3]
        if uuid_pattern.match(cid):
            if not (tombstones and cid in tombstones):
                all_conv_ids.add(cid)

    for pb_f in glob.glob(os.path.join(str(master_conv_dir), "*.pb")):
        cid = os.path.basename(pb_f)[:-3]
        if uuid_pattern.match(cid):
            if not (tombstones and cid in tombstones):
                all_conv_ids.add(cid)

    for cid in existing_rows.keys():
        if uuid_pattern.match(cid):
            if not (tombstones and cid in tombstones):
                all_conv_ids.add(cid)

    if extra_ids:
        for cid in extra_ids:
            if uuid_pattern.match(cid):
                if not (tombstones and cid in tombstones):
                    all_conv_ids.add(cid)

    return all_conv_ids


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
) -> None:
    """Evaluates and synchronizes an individual conversation entry in SQLite."""
    db_file = master_conv_dir / f"{conv_id}.db"
    has_db = db_file.is_file()
    pb_file = master_conv_dir / f"{conv_id}.pb"
    has_pb = pb_file.is_file()

    if has_db:
        file_mtime = db_file.stat().st_mtime
    elif has_pb:
        file_mtime = pb_file.stat().st_mtime
    elif conv_id in existing_rows and existing_rows[conv_id][3]:
        try:
            dt = datetime.datetime.fromisoformat(str(existing_rows[conv_id][3]).replace("Z", "+00:00"))
            file_mtime = dt.timestamp()
        except Exception:
            file_mtime = time.time()
    else:
        file_mtime = time.time()

    if file_mtime <= 1000000000:
        file_mtime = time.time()

    file_mtime_iso = datetime.datetime.fromtimestamp(file_mtime, tz=datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S.000000+00:00"
    )
    actual_steps = get_actual_steps_count(db_file) if has_db else (existing_rows[conv_id][2] if conv_id in existing_rows else 0)

    transcript_file = master_brain_dir / conv_id / ".system_generated" / "logs" / "transcript.jsonl"
    t_created, t_user_input, t_modified = get_transcript_timestamps(transcript_file)

    sql_mtime = _clean_iso_ts(existing_rows[conv_id][3]) if conv_id in existing_rows and existing_rows[conv_id][3] else None
    sql_user_input = (
        _clean_iso_ts(existing_rows[conv_id][5])
        if conv_id in existing_rows and len(existing_rows[conv_id]) > 5 and existing_rows[conv_id][5]
        else None
    )
    sql_user_step = (
        existing_rows[conv_id][6]
        if conv_id in existing_rows and len(existing_rows[conv_id]) > 6 and existing_rows[conv_id][6] is not None
        else -1
    )

    t_clean_created = _clean_iso_ts(t_created)
    t_clean_user_input = _clean_iso_ts(t_user_input)
    t_clean_modified = _clean_iso_ts(t_modified)

    final_modified_iso = t_clean_modified or sql_mtime or file_mtime_iso
    final_user_input_iso = t_clean_user_input or sql_user_input or final_modified_iso
    final_created_iso = t_clean_created or final_user_input_iso or final_modified_iso

    curr_raw = all_summaries.get(conv_id)
    parsed_raw = parse_cascade_summary(curr_raw) if curr_raw else {}
    raw_title = parsed_raw.get("title", "")
    raw_summary = parsed_raw.get("summary", "")

    sql_raw = existing_rows[conv_id][4] if conv_id in existing_rows else None
    parsed_sql = parse_cascade_summary(sql_raw) if sql_raw else {}
    sql_pinned = bool(parsed_sql.get("pinned", False))
    sql_archived = bool(parsed_sql.get("archived", False))

    raw_pinned = bool(parsed_raw.get("pinned", False))
    raw_archived = bool(parsed_raw.get("archived", False))

    anno_info = get_annotation_info(effective_master, conv_id)
    anno_title = anno_info.get("title")

    # Pinned: pinned_set (app_storage.json) is primary; fallback to anno_info, then proto/sqlite
    if pinned_set is not None and conv_id in pinned_set:
        is_pinned = True
    elif anno_info.get("exists") and anno_info.get("pinned") is not None:
        is_pinned = bool(anno_info.get("pinned"))
    else:
        is_pinned = raw_pinned or sql_pinned

    # Archived: anno_info if explicitly present; fallback to existing proto/sqlite state
    raw_arc = raw_archived
    sql_arc = sql_archived if conv_id in existing_rows else False
    if anno_info.get("exists") and anno_info.get("archived") is not None:
        is_archived = bool(anno_info.get("archived"))
    else:
        is_archived = raw_arc or sql_arc

    db_ws_uri, db_proj_id = get_db_trajectory_meta(db_file) if has_db else (None, None)

    curr_title = existing_rows[conv_id][0] if conv_id in existing_rows else ""
    curr_prev = existing_rows[conv_id][1] if conv_id in existing_rows else ""
    curr_step_cnt = existing_rows[conv_id][2] if conv_id in existing_rows else parsed_raw.get("step_count", 0)

    ext_t, ext_p = extract_conv_text(db_file, transcript_file)
    clean_ext_t = re.sub(r"(?:in\s*)?@\[[^\]]+\]", "", ext_t or "").strip()

    prompt_cands = extract_conv_prompts(db_file, transcript_file)
    if ext_p:
        prompt_cands.add(ext_p.strip())
        p_clean = re.sub(r"(?:in\s*)?@\[[^\]]+\]", "", ext_p).strip()
        if p_clean:
            prompt_cands.add(p_clean)

    # 1. Check existing titles (curr_title, anno_title, raw_title)
    # Prefer curr_title (master DB) if clean and not a prompt, to prevent IDE prompt overwrites
    existing_clean_title = ""
    for cand in [curr_title, anno_title, raw_title]:
        if (
            cand
            and is_clean_title(cand)
            and not is_prompt_text(cand, prompt_cands)
            and cand.strip() not in ["Conversation", "Untitled Conversation"]
        ):
            existing_clean_title = cand.strip()
            break

    # 2. Check LLM summaries (raw_summary, parsed_sql summary, curr_prev)
    llm_title = ""
    for cand in [raw_summary, parsed_sql.get("summary", ""), curr_prev]:
        if (
            cand
            and is_clean_title(cand)
            and not is_prompt_text(cand, prompt_cands)
            and cand.strip() not in ["Conversation", "Untitled Conversation"]
        ):
            llm_title = cand.strip()
            break

    # Priority: Existing clean title > Authentic LLM summary > Clean artifact title > "Conversation"
    if existing_clean_title:
        final_title = existing_clean_title
    elif llm_title:
        final_title = llm_title
    elif clean_ext_t and is_clean_title(clean_ext_t) and not is_prompt_text(clean_ext_t, prompt_cands):
        final_title = clean_ext_t
    else:
        final_title = "Conversation"

    final_prev = ext_p or curr_prev or raw_summary or clean_ext_t or final_title
    if not final_title:
        final_title = "Conversation"
    if not final_prev:
        final_prev = final_title

    target_step_cnt = max(actual_steps, curr_step_cnt, 1)
    existing_ws = existing_rows[conv_id][7] if conv_id in existing_rows and len(existing_rows[conv_id]) > 7 else None
    existing_proj = existing_rows[conv_id][8] if conv_id in existing_rows and len(existing_rows[conv_id]) > 8 else None

    raw_ws = db_ws_uri or parsed_raw.get("workspace_uri") or existing_ws
    ws_uri = normalize_workspace_uri(raw_ws)

    # Resolve project_id from authentic workspace mapping (using pre-discovered mappings O(1))
    mapped_pid = get_project_id_for_workspace(ws_uri, mappings=project_mappings) if ws_uri else None
    clean_mapped = mapped_pid if mapped_pid and mapped_pid != "outside-of-project" else ""
    clean_existing = existing_proj if existing_proj and existing_proj != "outside-of-project" else ""
    clean_db = db_proj_id if db_proj_id and db_proj_id != "outside-of-project" else ""
    clean_raw = parsed_raw.get("project_id") if parsed_raw.get("project_id") and parsed_raw.get("project_id") != "outside-of-project" else ""

    # Priority: Existing DB row PID > Authentic mapped PID > Trajectory meta PID > Raw proto PID
    proj_id = clean_existing or clean_mapped or clean_db or clean_raw or ""
    if not proj_id:
        proj_id = "outside-of-project"

    curr_raw_pid = parsed_raw.get("project_id") or ""
    existing_row_pid = existing_proj or ""
    target_pid = proj_id or ""
    needs_proj_rebuild = bool(
        (target_pid != curr_raw_pid)
        or (target_pid != existing_row_pid)
        or (target_pid and not parsed_raw.get("has_tag_18", False))
    )

    curr_raw_sum = (parsed_raw.get("summary") or "").strip()
    curr_raw_tit = (parsed_raw.get("title") or "").strip()
    expected_proto_sum = final_title if (is_clean_title(final_title) and final_title != "Conversation") else "---"

    has_dirty_title = bool("@[" in (curr_raw_tit or "") or "@[" in (curr_raw_sum or "") or "@[" in final_title)
    needs_title_rebuild = bool(
        curr_raw_tit != final_title
        or curr_raw_sum != expected_proto_sum
        or is_prompt_text(curr_raw_sum, prompt_cands)
        or is_prompt_text(curr_raw_tit, prompt_cands)
        or has_dirty_title
    )
    needs_ws_rebuild = bool(ws_uri and ws_uri != parsed_raw.get("workspace_uri"))
    has_bad_timestamps = bool(
        curr_raw
        and (
            b"\x80\x92\xb8\xc3\x98\xfe\xff\xff\xff\x01" in curr_raw
            or parsed_raw.get("has_bad_timestamp")
            or not parsed_raw.get("ts_3")
            or not parsed_raw.get("ts_10")
        )
    )
    has_trajectory_mismatch = bool(
        curr_raw
        and (
            not parsed_raw.get("trajectory_id")
            or parsed_raw.get("trajectory_id") != conv_id
        )
    )
    is_corrupt_raw = bool(
        has_bad_timestamps
        or has_trajectory_mismatch
        or (curr_raw and any(ord(c) < 32 and c not in "\n\r\t\x1b\x0c" for c in (raw_summary or "")))
    )
    needs_steps_rebuild = bool(actual_steps > curr_step_cnt)
    is_not_in_sqlite = bool(conv_id not in existing_rows)

    needs_pinned_rebuild = bool(
        is_pinned != raw_pinned
        or is_archived != raw_archived
        or is_pinned != sql_pinned
        or is_archived != sql_archived
    )
    sql_clean = extract_pure_binary_summary(sql_raw) if sql_raw else None
    curr_clean = extract_pure_binary_summary(curr_raw) if curr_raw else None
    needs_sql_sync = bool(is_not_in_sqlite or (sql_clean != curr_clean))

    needs_blob_repair = False
    if has_db:
        try:
            with sqlite3.connect(str(db_file), timeout=0.5) as check_conn:
                row = check_conn.execute("SELECT data FROM trajectory_metadata_blob WHERE id = 'main'").fetchone()
                bdata = row[0] if row else None
                if not bdata or len(bdata) < 10 or bdata.startswith(b"de0c") or bdata.startswith(b"770a"):
                    needs_blob_repair = True
        except Exception:
            needs_blob_repair = True

    needs_source_rebuild = bool(
        parsed_raw.get("source") == 1
        or parsed_raw.get(20) == 1
    )

    # If summary exists, is valid, is in SQLite, and doesn't need rebuild:
    if (
        curr_raw
        and len(curr_raw) > 20
        and not needs_title_rebuild
        and not is_corrupt_raw
        and not needs_steps_rebuild
        and not is_not_in_sqlite
        and not needs_ws_rebuild
        and not needs_proj_rebuild
        and not needs_pinned_rebuild
        and not needs_sql_sync
        and not needs_blob_repair
        and not needs_source_rebuild
    ):
        all_summaries[conv_id] = curr_raw
        if curr_title != final_title or curr_prev != final_prev:
            cur.execute(
                "UPDATE conversation_summaries SET title=?, preview=? WHERE conversation_id=?;",
                (final_title, final_prev, conv_id),
            )
            stats.conversations_updated += 1
            stats.dirty_conv_ids.add(conv_id)
        return

    # Reconstruct authentic summary if needed, or reuse valid existing binary
    if (
        curr_raw
        and len(curr_raw) > 20
        and not needs_title_rebuild
        and not is_corrupt_raw
        and not needs_steps_rebuild
        and not needs_ws_rebuild
        and not needs_proj_rebuild
        and not needs_source_rebuild
        and (is_pinned == raw_pinned and is_archived == raw_archived)
    ):
        raw_to_store = curr_raw
        user_step = (
            parsed_raw.get("last_user_step")
            if parsed_raw.get("last_user_step") is not None
            else (sql_user_step if sql_user_step >= 0 else get_last_user_step_index(db_file, target_step_cnt))
        )
    else:
        user_step = (
            sql_user_step
            if sql_user_step >= 0
            else get_last_user_step_index(db_file, target_step_cnt)
        )
        proto_summary = final_title if (is_clean_title(final_title) and final_title != "Conversation") else "---"
        raw_to_store = build_cascade_summary(
            conv_id,
            final_title,
            proto_summary,
            target_step_cnt,
            last_modified_iso=final_modified_iso,
            last_user_step=user_step,
            workspace_uri=ws_uri,
            project_id=proj_id,
            created_iso=final_created_iso,
            last_user_input_iso=final_user_input_iso,
            pinned=is_pinned,
            archived=is_archived,
        )

    all_summaries[conv_id] = raw_to_store

    ws_str = ""
    if ws_uri:
        ws_str = ws_uri if str(ws_uri).startswith("[") else json.dumps([str(ws_uri)])

    summary_model = ConversationSummary(
        conversation_id=conv_id,
        title=final_title,
        preview=final_prev,
        step_count=target_step_cnt,
        last_modified_time=final_modified_iso,
        last_user_input_time=final_user_input_iso,
        last_user_input_step_index=user_step,
        raw_summary=raw_to_store,
        workspace_uris=ws_str,
        project_id=proj_id or "",
        source="",
    )
    upsert_summary(con, summary_model)
    if final_title and is_clean_title(final_title) and not is_prompt_text(final_title, prompt_cands):
        sync_annotation_file(effective_master, conv_id, final_title, pinned=is_pinned, archived=is_archived, force=True)
    else:
        # No authentic title: clean up stale prompt annotation file if present
        anno_file = effective_master / "annotations" / f"{conv_id}.pbtxt"
        if anno_file.is_file():
            try:
                content = anno_file.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r'title\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', content)
                if m:
                    existing_t = m.group(1).strip()
                    if not is_clean_title(existing_t) or is_prompt_text(existing_t, prompt_cands):
                        new_content = re.sub(r'\s*title\s*:\s*"[^"\\]*(?:\\.[^"\\]*)*"', '', content).strip()
                        has_pin = bool(re.search(r'pinned\s*:\s*true', new_content, re.IGNORECASE))
                        has_arc = bool(re.search(r'archived\s*:\s*true', new_content, re.IGNORECASE))
                        if not has_pin and not has_arc and not re.search(r'title\s*:\s*"[^"]+"', new_content):
                            os.remove(str(anno_file))
                        else:
                            anno_file.write_text(new_content + "\n", encoding="utf-8")
            except Exception:
                pass
        elif is_pinned or is_archived:
            sync_annotation_file(effective_master, conv_id, "Conversation", pinned=is_pinned, archived=is_archived, force=False)

    # Keep conversation db trajectory_metadata_blob in sync if present
    if has_db and (needs_blob_repair or (ws_uri and (ws_uri != db_ws_uri or proj_id != db_proj_id))):
        try:
            with sqlite3.connect(str(db_file), timeout=1.0) as conv_conn:
                conv_conn.execute("PRAGMA busy_timeout = 1000;")
                conv_conn.execute("CREATE TABLE IF NOT EXISTS trajectory_metadata_blob (id text DEFAULT 'main', data blob, PRIMARY KEY (id));")
                new_blob = build_trajectory_metadata_blob(conv_id, ws_uri or "file:///tmp", proj_id or "outside-of-project")
                conv_conn.execute("INSERT OR REPLACE INTO trajectory_metadata_blob (id, data) VALUES ('main', ?);", (new_blob,))
                conv_conn.commit()
        except sqlite3.OperationalError:
            # Active chat holds write lock; skip non-critical background update to avoid lock contention
            pass
        except Exception:
            pass

    if is_not_in_sqlite:
        stats.summaries_backfilled += 1
    else:
        stats.conversations_updated += 1
    stats.dirty_conv_ids.add(conv_id)


def synchronize_master_summaries(
    effective_master: Path,
    master_conv_dir: Path,
    master_brain_dir: Path,
    master_sum_db: Path,
    master_proto: Path,
    stats: SyncStats,
    pinned_set: Optional[Set[str]] = None,
    user_home: Optional[Path] = None,
    tombstones: Optional[Set[str]] = None,
) -> Tuple[sqlite3.Connection, Dict[str, bytes]]:
    """
    Connects to master SQLite database, ensures schema, ingests existing summaries,
    evaluates all conversations, and writes back authentic records.
    Returns:
        (con, all_summaries)
    """
    home = user_home or get_user_home()
    all_summaries: Dict[str, bytes] = {}
    con = sqlite3.connect(str(master_sum_db), timeout=15.0)
    ensure_summaries_schema(con)
    cur = con.cursor()
    cur.execute("UPDATE conversation_summaries SET source='' WHERE source='CORTEX_TRAJECTORY_SOURCE_CASCADE_CLIENT';")
    con.commit()
    existing_rows = load_existing_summaries(master_sum_db)

    # Ingest existing valid summaries from SQLite
    for c_id, row in existing_rows.items():
        if tombstones and c_id in tombstones:
            continue
        if row[4]:
            raw = extract_pure_binary_summary(row[4])
            if raw and len(raw) > 20:
                all_summaries[c_id] = raw

    # Ingest master protobuf binary summaries if available
    if master_proto.is_file():
        try:
            with open(master_proto, "rb") as f:
                proto_data = f.read()
            for c_uuid, raw in extract_entries_from_proto(proto_data).items():
                if tombstones and c_uuid in tombstones:
                    continue
                if raw and len(raw) > 20 and c_uuid not in all_summaries:
                    all_summaries[c_uuid] = raw
        except Exception:
            pass

    all_conv_ids = collect_all_conversation_ids(
        master_conv_dir=master_conv_dir,
        existing_rows=existing_rows,
        extra_ids=all_summaries.keys(),
        tombstones=tombstones,
    )

    # Pre-discover project mappings once in memory (O(1) resolution)
    project_mappings = discover_project_mappings(home)

    for conv_id in sorted(all_conv_ids):
        resolve_conversation_item(
            conv_id=conv_id,
            effective_master=effective_master,
            master_conv_dir=master_conv_dir,
            master_brain_dir=master_brain_dir,
            existing_rows=existing_rows,
            all_summaries=all_summaries,
            cur=cur,
            con=con,
            stats=stats,
            pinned_set=pinned_set,
            project_mappings=project_mappings,
        )

    con.commit()
    return con, all_summaries


def serialize_master_proto(master_proto: Path, all_summaries: Dict[str, bytes]) -> bool:
    """Serializes in-memory summaries dictionary to binary Protobuf file atomically if changed."""
    try:
        entries_data = bytearray()
        for u_id, p_bin in sorted(all_summaries.items()):
            raw = extract_pure_binary_summary(p_bin)
            if raw and len(raw) >= 10:
                entry = bytearray()
                entry += encode_tag_bytes(1, u_id.encode("utf-8"))
                entry += encode_tag_bytes(2, raw)
                entries_data += encode_tag_bytes(1, bytes(entry))

        new_bytes = bytes(entries_data)
        if master_proto.is_file():
            try:
                if master_proto.stat().st_size == len(new_bytes):
                    with open(master_proto, "rb") as cur_f:
                        if cur_f.read() == new_bytes:
                            return False  # Unchanged! Skip writing to disk and companion copies
            except Exception:
                pass

        tmp_proto = str(master_proto) + ".tmp"
        with open(tmp_proto, "wb") as f:
            f.write(new_bytes)
        os.replace(tmp_proto, master_proto)

        # Atomically synchronize companion protobuf files in master directory
        parent_dir = master_proto.parent
        for companion_name in [
            "jetbox_summaries.pb",
            "jetbox_summaries_proto.pb",
            "agyhub_summaries.pb",
        ]:
            companion_file = parent_dir / companion_name
            if companion_file.exists():
                try:
                    if not companion_file.is_symlink():
                        shutil.copy2(master_proto, companion_file)
                except Exception:
                    pass
        return True
    except Exception:
        return False


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
                is_arc = False
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


def merge_histories(
    master_gemini: Optional[Union[str, Path]] = None,
    source_dir: Optional[Union[str, Path]] = None,
    target_dir: Optional[Union[str, Path]] = None,
    quiet: bool = False,
    force_rebuild: bool = False,
    user_home: Optional[Union[str, Path]] = None,
    skip_backup: bool = False,
) -> SyncStats:
    """
    Performs full 3-way synchronization between Antigravity Hub, Antigravity IDE,
    and all isolated multi-account profiles with automated transactional backup.
    """
    home = Path(user_home).resolve() if user_home else get_user_home()
    effective_master = (
        Path(master_gemini).resolve()
        if master_gemini
        else Path(
            os.environ.get(
                "ANTIGRAVITY_DATA_DIR",
                os.environ.get("ANTIGRAVITY_HISTORY_DIR", home / ".gemini" / "antigravity")
            )
        ).resolve()
    )

    # 0. Ensure authentic project JSON configs exist in ~/.gemini/config/projects/
    ensure_project_configs(user_home=home)

    # 1. Setup master directories & symlinks
    (
        master_conv_dir,
        master_brain_dir,
        master_sum_db,
        master_proto,
        master_anno,
    ) = setup_master_directories(effective_master)

    stats = SyncStats()

    # 2. Discover all history pools and candidate VSCDBs across the system
    conv_pools, brain_pools, ide_candidates = discover_all_history_sources(
        target_dir=target_dir,
        user_home=home,
        source_dir=source_dir,
    )
    candidate_vscdbs = discover_candidate_vscdbs(home, ide_candidates)
    stats.conv_stores_scanned = len(conv_pools)
    stats.brain_stores_scanned = len(brain_pools)

    # 3. Create automated pre-merge backup snapshot before making any modifications
    if not skip_backup:
        backup_entry = HistoryBackupManager.create_pre_merge_backup(
            effective_master=effective_master,
            candidate_vscdbs=candidate_vscdbs,
            user_home=home,
            description="Pre-merge automatic backup",
        )
        if backup_entry:
            stats.backup_id = backup_entry.backup_id

    # 3.5. Load permanent tombstones to prevent resurrection of deleted chats
    tombstones = get_tombstones(effective_master)

    # 4. Merge raw .db and .pb pools into master
    stats.db_files_merged = merge_raw_db_pools(conv_pools, master_conv_dir, tombstones=tombstones)

    # 5. Merge brain folders into master
    stats.brain_folders_merged = merge_brain_folders(brain_pools, master_brain_dir, tombstones=tombstones)

    # 6. Reconstruct missing databases from transcript logs
    stats.databases_reconstructed = reconstruct_missing_databases(
        brain_pools=brain_pools,
        master_brain_dir=master_brain_dir,
        master_conv_dir=master_conv_dir,
        force_rebuild=force_rebuild,
        tombstones=tombstones,
    )

    # 6.5. Discover and unify all pinned conversations across Desktop App profiles
    pinned_ids = discover_pinned_conversation_ids(user_home=home)
    replicate_pinned_conversations_order(pinned_ids, user_home=home)

    # 7. Read and synchronize conversation_summaries.db
    con, all_summaries = synchronize_master_summaries(
        effective_master=effective_master,
        master_conv_dir=master_conv_dir,
        master_brain_dir=master_brain_dir,
        master_sum_db=master_sum_db,
        master_proto=master_proto,
        stats=stats,
        pinned_set=pinned_ids,
        user_home=home,
        tombstones=tombstones,
    )

    try:
        cur = con.cursor()

        # 7.5. Detect and synchronize bi-directional deletions across App and IDE
        stats.conversations_deleted = detect_and_sync_deletions(
            effective_master=effective_master,
            con=con,
            candidate_vscdbs=candidate_vscdbs,
            conv_pools=conv_pools,
            brain_pools=brain_pools,
            all_summaries=all_summaries,
            stats=stats,
        )

        # 8. Enrich summaries with authentic titles from VS Code state.vscdb
        stats.ide_state_ingested = ingest_vscdb_summaries(
            candidate_vscdbs=candidate_vscdbs,
            all_summaries=all_summaries,
            master_conv_dir=master_conv_dir,
            con=con,
            pinned_set=pinned_ids,
            tombstones=tombstones,
        )


        # 9. Serialize and write agyhub_summaries_proto.pb
        serialize_master_proto(master_proto, all_summaries)

        # 10. Update state.vscdb across all IDE profiles
        write_vscdb_unified_state(candidate_vscdbs, all_summaries)

        # Flush SQLite WAL to disk so replicated files have complete state
        try:
            cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            con.commit()
        except Exception:
            pass

        # 11. Replicate conversation_summaries.db and proto to target IDE profiles
        replicate_to_ide_profiles(
            target_ide_dirs=ide_candidates,
            effective_master=effective_master,
            master_sum_db=master_sum_db,
            master_conv_dir=master_conv_dir,
            master_proto=master_proto,
            con=con,
        )

        # 12. Synchronize annotations/<conv_id>.pbtxt files for Desktop App UI title rendering
        target_annos = None if force_rebuild else stats.dirty_conv_ids
        sync_annotation_files(effective_master, cur, pinned_set=pinned_ids, target_conv_ids=target_annos)

        stats.total_active_history = cur.execute("SELECT count(*) FROM conversation_summaries;").fetchone()[0]

        # Final WAL checkpoint
        try:
            cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            con.commit()
        except Exception:
            pass
    finally:
        con.close()

    # 13. Automatically refresh IDE OAuth token if expired
    cfg = SuiteConfig(user_home=home)
    for ide_dir in cfg.ide_dirs:
        refresh_ide_oauth_token(ide_dir, home)

    return stats
