"""
Unified History Synchronization and Merge Engine for Antigravity Suite.

Synchronizes conversation databases, SQLite indexes, Protobuf binary indexes,
and VS Code global storage state across Desktop App and IDE instances.
"""

from __future__ import annotations

import base64
import datetime
import glob
import json
import os
import re
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from antigravity_suite.auth.token import refresh_ide_oauth_token
from antigravity_suite.config import DEFAULT_CONFIG, get_user_home
from antigravity_suite.history.discovery import discover_all_history_sources
from antigravity_suite.history.extractor import (
    extract_conv_text,
    get_annotation_title,
    sync_annotation_file,
)
from antigravity_suite.history.models import ConversationSummary, SyncStats
from antigravity_suite.history.sqlite_store import (
    ensure_summaries_schema,
    get_actual_steps_count,
    load_existing_summaries,
    upsert_summary,
)
from antigravity_suite.history.synthesizer import (
    is_synthesized_db_incomplete,
    synthesize_db_from_transcript,
)
from antigravity_suite.proto.cascade import (
    build_cascade_summary,
    get_last_user_step_index,
    parse_cascade_summary,
)
from antigravity_suite.proto.vscdb import (
    build_summaries_state,
    build_unified_state_sync,
)
from antigravity_suite.proto.wire import (
    encode_tag_bytes,
    extract_entries_from_proto,
    extract_pure_binary_summary,
)


def merge_histories(
    master_gemini: Optional[Union[str, Path]] = None,
    source_dir: Optional[Union[str, Path]] = None,
    target_dir: Optional[Union[str, Path]] = None,
    quiet: bool = False,
    force_rebuild: bool = False,
    user_home: Optional[Union[str, Path]] = None,
) -> SyncStats:
    """
    Performs full 3-way synchronization between Antigravity Hub, Antigravity IDE,
    and all isolated multi-account profiles.
    """
    home = Path(user_home).resolve() if user_home else get_user_home()
    effective_master = (
        Path(master_gemini).resolve()
        if master_gemini
        else Path(os.environ.get("ANTIGRAVITY_APP_DIR", home / ".gemini" / "antigravity")).resolve()
    )

    master_conv_dir = effective_master / "conversations"
    master_brain_dir = effective_master / "brain"
    master_sum_db = effective_master / "conversation_summaries.db"
    sub_sum_db = master_conv_dir / "conversation_summaries.db"
    master_proto = effective_master / "agyhub_summaries_proto.pb"
    master_anno = effective_master / "annotations"

    master_conv_dir.mkdir(parents=True, exist_ok=True)
    master_brain_dir.mkdir(parents=True, exist_ok=True)
    master_anno.mkdir(parents=True, exist_ok=True)

    # Migrate and maintain symlink: master_conv_dir / conversation_summaries.db -> ../conversation_summaries.db
    if sub_sum_db.exists() and not sub_sum_db.is_symlink():
        if not master_sum_db.exists():
            try:
                shutil.move(str(sub_sum_db), str(master_sum_db))
            except Exception:
                pass
        try:
            if not sub_sum_db.is_symlink():
                if sub_sum_db.exists():
                    os.remove(str(sub_sum_db))
                sub_sum_db.symlink_to("../conversation_summaries.db")
        except Exception:
            pass
    elif not sub_sum_db.exists() and master_sum_db.exists():
        try:
            sub_sum_db.symlink_to("../conversation_summaries.db")
        except Exception:
            pass

    stats = SyncStats()

    # 1. Discover all history pools across the system
    conv_pools, brain_pools, ide_candidates = discover_all_history_sources(target_dir, home)
    stats.conv_stores_scanned = len(conv_pools)
    stats.brain_stores_scanned = len(brain_pools)

    # 2. Merge raw .db and .pb files into master pool
    for pool in conv_pools:
        if os.path.realpath(pool) == str(master_conv_dir):
            continue
        for src_file in glob.glob(os.path.join(pool, "*")):
            base = os.path.basename(src_file)
            if not (base.endswith(".db") or base.endswith(".pb")):
                continue
            if base == "conversation_summaries.db":
                continue
            target_file = master_conv_dir / base
            if not target_file.exists():
                try:
                    shutil.copy2(src_file, target_file)
                    stats.db_files_merged += 1
                except Exception:
                    pass
            elif target_file.stat().st_size == 0 and os.path.getsize(src_file) > 0:
                try:
                    shutil.copy2(src_file, target_file)
                    stats.db_files_merged += 1
                except Exception:
                    pass

    # 3. Merge brain folders & Reconstruct missing databases from transcripts
    reconstructed_uuids: Set[str] = set()
    for b_pool in brain_pools:
        if os.path.realpath(b_pool) != str(master_brain_dir):
            for b_item in glob.glob(os.path.join(b_pool, "*")):
                if not os.path.isdir(b_item):
                    continue
                c_uuid = os.path.basename(b_item)
                if not re.match(r"^[0-9a-fA-F-]{36}$", c_uuid):
                    continue
                target_brain_item = master_brain_dir / c_uuid
                if not target_brain_item.exists():
                    try:
                        shutil.copytree(b_item, target_brain_item, symlinks=True)
                        stats.brain_folders_merged += 1
                    except Exception:
                        pass

        # Reconstruct missing databases from transcript logs
        for b_item in glob.glob(os.path.join(b_pool, "*")):
            if not os.path.isdir(b_item):
                continue
            c_uuid = os.path.basename(b_item)
            if not re.match(r"^[0-9a-fA-F-]{36}$", c_uuid):
                continue
            if c_uuid in reconstructed_uuids:
                continue

            target_db = master_conv_dir / f"{c_uuid}.db"
            tf = os.path.join(b_item, ".system_generated", "logs", "transcript_full.jsonl")
            if not os.path.isfile(tf):
                tf = os.path.join(b_item, ".system_generated", "logs", "transcript.jsonl")

            if os.path.isfile(tf):
                if not target_db.exists() or is_synthesized_db_incomplete(target_db) or force_rebuild:
                    if synthesize_db_from_transcript(c_uuid, target_db, tf):
                        stats.databases_reconstructed += 1
                        reconstructed_uuids.add(c_uuid)

    # 4. Read and Synchronize conversation_summaries.db
    all_summaries: Dict[str, bytes] = {}
    con = sqlite3.connect(str(master_sum_db), timeout=15.0)
    ensure_summaries_schema(con)
    cur = con.cursor()
    existing_rows = load_existing_summaries(master_sum_db)

    # Ingest existing valid summaries from SQLite
    for c_id, row in existing_rows.items():
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
                if raw and len(raw) > 20:
                    all_summaries[c_uuid] = raw
        except Exception:
            pass

    # Collect all conversation IDs across DBs, PBs, and existing rows
    all_conv_ids: Set[str] = set()
    for db_f in glob.glob(os.path.join(str(master_conv_dir), "*.db")):
        cid = os.path.basename(db_f)[:-3]
        if re.match(r"^[0-9a-fA-F-]{36}$", cid):
            all_conv_ids.add(cid)
    for pb_f in glob.glob(os.path.join(str(master_conv_dir), "*.pb")):
        cid = os.path.basename(pb_f)[:-3]
        if re.match(r"^[0-9a-fA-F-]{36}$", cid):
            all_conv_ids.add(cid)
    for cid in existing_rows.keys():
        if re.match(r"^[0-9a-fA-F-]{36}$", cid):
            all_conv_ids.add(cid)

    for conv_id in sorted(all_conv_ids):
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

        file_mtime_iso = datetime.datetime.fromtimestamp(file_mtime, tz=datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S.000000+00:00"
        )
        actual_steps = get_actual_steps_count(db_file) if has_db else (existing_rows[conv_id][2] if conv_id in existing_rows else 0)

        transcript_file = master_brain_dir / conv_id / ".system_generated" / "logs" / "transcript.jsonl"
        anno_title = get_annotation_title(effective_master, conv_id)

        if conv_id in all_summaries:
            curr_raw = all_summaries[conv_id]
            parsed_raw = parse_cascade_summary(curr_raw)
            raw_title = parsed_raw.get("title", "")
            raw_summary = parsed_raw.get("summary", "")

            curr_title = existing_rows.get(conv_id, ("",))[0] if conv_id in existing_rows else ""
            curr_prev = existing_rows.get(conv_id, ("", "", ""))[1] if conv_id in existing_rows else ""

            final_title = anno_title or curr_title or raw_title
            final_prev = curr_prev or raw_summary

            if not final_title or final_title.strip() == "" or final_title in ["Conversation", "Untitled Conversation"]:
                if curr_prev and curr_prev.strip() and curr_prev not in ["Conversation", "Untitled Conversation"]:
                    final_title = curr_prev.strip().split("\n")[0][:80]
                elif raw_summary and raw_summary.strip() and raw_summary not in ["Conversation", "Untitled Conversation"]:
                    final_title = raw_summary.strip().split("\n")[0][:80]

            if not final_title or final_title.strip() == "" or final_title in ["Conversation", "Untitled Conversation"]:
                ext_t, ext_p = extract_conv_text(db_file, transcript_file)
                if ext_t:
                    final_title = ext_t
                    final_prev = ext_p or final_prev

            curr_raw_title = parsed_raw.get("title") or parsed_raw.get("summary")
            needs_title_rebuild = bool(
                final_title
                and (
                    not curr_raw_title
                    or curr_raw_title in ["Conversation", "Untitled Conversation"]
                )
            )
            is_corrupt_raw = bool(curr_raw and any(ord(c) < 32 and c not in "\n\r\t" for c in (raw_summary or "")))

            if curr_raw and len(curr_raw) > 20 and not needs_title_rebuild and not is_corrupt_raw:
                all_summaries[conv_id] = curr_raw
                if curr_title != final_title or curr_prev != final_prev:
                    cur.execute(
                        "UPDATE conversation_summaries SET title=?, preview=? WHERE conversation_id=?;",
                        (final_title, final_prev, conv_id),
                    )
                    stats.conversations_updated += 1
                continue

        # Ingest from existing SQLite row
        if conv_id in existing_rows:
            curr_title, curr_prev, curr_step_cnt, curr_mtime, curr_raw_blob = existing_rows[conv_id]
            pure_bin = extract_pure_binary_summary(curr_raw_blob)
            final_title = anno_title or curr_title
            final_prev = curr_prev
            if not final_title or final_title in ["Conversation", "Untitled Conversation"]:
                ext_t, ext_p = extract_conv_text(db_file, transcript_file)
                if ext_t:
                    final_title = ext_t
                    final_prev = ext_p or final_prev

            if pure_bin and len(pure_bin) > 20:
                parsed = parse_cascade_summary(pure_bin)
                raw_t = parsed.get("title") or parsed.get("summary")
                if not final_title or final_title in ["Conversation", "Untitled Conversation"]:
                    final_title = raw_t or final_title

            if final_title and final_title not in ["Conversation", "Untitled Conversation"]:
                step_cnt = max(actual_steps, curr_step_cnt, 1)
                user_step = get_last_user_step_index(db_file, step_cnt)

                if pure_bin and len(pure_bin) > 20 and curr_title == final_title and curr_step_cnt == step_cnt:
                    all_summaries[conv_id] = pure_bin
                    continue

                new_bin = build_cascade_summary(
                    conv_id,
                    final_title,
                    final_prev or final_title,
                    step_cnt,
                    file_mtime_iso,
                    last_user_step=user_step,
                )
                all_summaries[conv_id] = new_bin
                cur.execute(
                    "UPDATE conversation_summaries SET title=?, preview=?, step_count=?, last_modified_time=?, raw_summary=? WHERE conversation_id=?;",
                    (final_title, final_prev or final_title, step_cnt, file_mtime_iso, new_bin, conv_id),
                )
                stats.conversations_updated += 1
                continue

        # Generate new authentic summary
        title, preview = extract_conv_text(db_file, transcript_file)
        if anno_title:
            title = anno_title
        if not title:
            title = "Conversation"
        if not preview:
            preview = title

        step_cnt = max(actual_steps, 1)
        user_step = get_last_user_step_index(db_file, step_cnt)
        pure_bin = build_cascade_summary(
            conv_id,
            title,
            preview,
            step_cnt,
            file_mtime_iso,
            last_user_step=user_step,
        )
        all_summaries[conv_id] = pure_bin

        summary_model = ConversationSummary(
            conversation_id=conv_id,
            title=title,
            preview=preview,
            step_count=step_cnt,
            last_modified_time=file_mtime_iso,
            last_user_input_step_index=user_step,
            raw_summary=pure_bin,
        )
        upsert_summary(con, summary_model)
        stats.summaries_backfilled += 1

    con.commit()

    # 5. Read titles from VS Code state.vscdb
    state_vscdb = home / ".config" / "Antigravity IDE" / "User" / "globalStorage" / "state.vscdb"
    if state_vscdb.is_file():
        try:
            v_con = sqlite3.connect(str(state_vscdb), timeout=15.0)
            v_cur = v_con.cursor()
            rows = v_cur.execute(
                "SELECT value FROM ItemTable WHERE key IN ('antigravityUnifiedStateSync.trajectorySummaries', 'antigravityUnifiedStateSync');"
            ).fetchall()
            for r in rows:
                val = r[0]
                if not val:
                    continue
                v_bin = base64.b64decode(val)
                entries = extract_entries_from_proto(v_bin)
                for u_id, p_bin in entries.items():
                    raw = extract_pure_binary_summary(p_bin)
                    if raw:
                        parsed = parse_cascade_summary(raw)
                        ide_title = parsed.get("title") or parsed.get("summary")
                        if u_id in all_summaries:
                            curr_parsed = parse_cascade_summary(all_summaries[u_id])
                            curr_t = curr_parsed.get("title") or curr_parsed.get("summary")
                            if ide_title and (
                                not curr_t or curr_t in ["Conversation", "IDE Conversation", "Untitled Conversation"]
                            ):
                                sc = curr_parsed.get(2, 1)
                                db_p = master_conv_dir / f"{u_id}.db"
                                user_step = get_last_user_step_index(db_p, sc)
                                new_bin = build_cascade_summary(
                                    u_id, ide_title, ide_title, sc, last_user_step=user_step
                                )
                                all_summaries[u_id] = new_bin
                                cur.execute(
                                    "UPDATE conversation_summaries SET title=?, raw_summary=? WHERE conversation_id=?",
                                    (ide_title, new_bin, u_id),
                                )
            v_con.close()
            con.commit()
        except Exception:
            pass

    # 6. Serialize and write agyhub_summaries_proto.pb
    try:
        entries_data = bytearray()
        for u_id, p_bin in sorted(all_summaries.items()):
            raw = extract_pure_binary_summary(p_bin)
            if raw and len(raw) >= 10:
                entry = bytearray()
                entry += encode_tag_bytes(1, u_id.encode("utf-8"))
                entry += encode_tag_bytes(2, raw)
                entries_data += encode_tag_bytes(1, bytes(entry))

        tmp_proto = str(master_proto) + ".tmp"
        with open(tmp_proto, "wb") as f:
            f.write(bytes(entries_data))
        os.replace(tmp_proto, master_proto)
    except Exception:
        pass

    # 7. Update state.vscdb across all IDE profiles
    if state_vscdb.is_file():
        try:
            val_wrap_b64 = build_summaries_state(all_summaries)
            outer_b64 = build_unified_state_sync(all_summaries)
            v_con = sqlite3.connect(str(state_vscdb), timeout=15.0)
            v_cur = v_con.cursor()
            v_cur.execute(
                "INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync.trajectorySummaries', ?);",
                (val_wrap_b64,),
            )
            v_cur.execute(
                "INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync', ?);",
                (outer_b64,),
            )
            v_con.commit()
            v_con.close()
            stats.ide_state_ingested = 1
        except Exception:
            pass

    # Flush SQLite WAL to disk so replicated files have complete state
    try:
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        con.commit()
    except Exception:
        pass

    # 8. Replicate conversation_summaries.db and proto to target IDE profiles
    target_ide_dirs = []
    for td in sorted(set(ide_candidates)):
        if os.path.isdir(td) and os.path.realpath(td) != str(effective_master):
            if "suite-manager" in os.path.basename(td):
                continue
            target_ide_dirs.append(td)

    for target_d in target_ide_dirs:
        try:
            tgt_conv_dir = os.path.join(target_d, "conversations")
            os.makedirs(tgt_conv_dir, exist_ok=True)

            # Replicate canonical conversation_summaries.db using SQLite backup API
            tgt_root_sum_db = os.path.join(target_d, "conversation_summaries.db")
            if not os.path.islink(tgt_root_sum_db) and not (
                os.path.exists(tgt_root_sum_db) and os.path.samefile(str(master_sum_db), tgt_root_sum_db)
            ):
                try:
                    dest_c = sqlite3.connect(tgt_root_sum_db, timeout=15.0)
                    con.backup(dest_c)
                    dest_c.close()
                except Exception:
                    pass

            t_sum_db = os.path.join(tgt_conv_dir, "conversation_summaries.db")
            if not os.path.islink(t_sum_db) and not (
                os.path.exists(t_sum_db) and os.path.samefile(str(master_sum_db), t_sum_db)
            ):
                try:
                    # Prefer relative symlink to root conversation_summaries.db if possible
                    if os.path.exists(tgt_root_sum_db) and not os.path.exists(t_sum_db):
                        try:
                            os.symlink("../conversation_summaries.db", t_sum_db)
                        except Exception:
                            dest_c = sqlite3.connect(t_sum_db, timeout=15.0)
                            con.backup(dest_c)
                            dest_c.close()
                    else:
                        dest_c = sqlite3.connect(t_sum_db, timeout=15.0)
                        con.backup(dest_c)
                        dest_c.close()
                except Exception:
                    pass

            if not os.path.islink(tgt_conv_dir) and not os.path.samefile(str(master_conv_dir), tgt_conv_dir):
                for db_src in glob.glob(os.path.join(str(master_conv_dir), "*.db")):
                    tgt_db = os.path.join(tgt_conv_dir, os.path.basename(db_src))
                    if not os.path.exists(tgt_db) or os.path.getsize(tgt_db) == 0:
                        try:
                            shutil.copy2(db_src, tgt_db)
                        except Exception:
                            pass

            t_proto = os.path.join(target_d, "agyhub_summaries_proto.pb")
            if master_proto.is_file():
                if not os.path.islink(t_proto) and not (
                    os.path.exists(t_proto) and os.path.samefile(str(master_proto), t_proto)
                ):
                    shutil.copy2(master_proto, t_proto)
        except Exception:
            pass

    # 9. Synchronize annotations/<conv_id>.pbtxt files for Desktop App UI title rendering
    for c_id, c_title in cur.execute(
        "SELECT conversation_id, title FROM conversation_summaries WHERE length(title) > 0;"
    ).fetchall():
        sync_annotation_file(effective_master, c_id, c_title)

    stats.total_active_history = cur.execute("SELECT count(*) FROM conversation_summaries;").fetchone()[0]

    # Final WAL checkpoint before closing master connection
    try:
        cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        con.commit()
    except Exception:
        pass
    con.close()

    # 10. Automatically refresh IDE OAuth token if expired
    for ide_dir in DEFAULT_CONFIG.ide_dirs:
        refresh_ide_oauth_token(ide_dir, home)

    return stats
