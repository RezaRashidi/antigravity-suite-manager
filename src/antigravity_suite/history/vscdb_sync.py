"""
VS Code Global Storage (state.vscdb) Synchronization Engine.

Extracts authentic conversation titles from IDE state.vscdb storage and mirrors
unified Protobuf state sync back to IDE globalStorage databases.
"""

from __future__ import annotations

import base64
import glob
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from antigravity_suite.history.extractor import (
    extract_conv_prompts,
    extract_conv_text,
    is_clean_title,
    is_prompt_text,
    sync_annotation_file,
)
from antigravity_suite.history.projects import (
    get_project_id_for_workspace,
    is_valid_workspace_uri,
    normalize_workspace_uri,
)
from antigravity_suite.history.sqlite_store import get_actual_steps_count
from antigravity_suite.proto.cascade import build_cascade_summary, get_last_user_step_index, parse_cascade_summary
from antigravity_suite.proto.trajectory import parse_trajectory_metadata_blob
from antigravity_suite.proto.vscdb import (
    build_summaries_state,
    build_unified_state_sync,
    update_sidebar_workspaces_state,
)
from antigravity_suite.proto.wire import extract_entries_from_proto, extract_pure_binary_summary


def get_db_trajectory_meta(db_path: Union[str, Path]) -> Tuple[Optional[str], Optional[str]]:
    """Reads workspace_uri and project_id from trajectory_metadata_blob if present."""
    p = Path(db_path)
    if not p.is_file():
        return None, None
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=15.0)
        row = conn.cursor().execute("SELECT data FROM trajectory_metadata_blob WHERE id = 'main';").fetchone()
        if row and row[0]:
            meta = parse_trajectory_metadata_blob(row[0])
            uris = meta.get("workspace_uris", [])
            w_uri = uris[0] if uris else meta.get("workspace_uri")
            return w_uri, meta.get("project_id")
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return None, None


def discover_candidate_vscdbs(
    user_home: Path,
    ide_candidates: Optional[List[str]] = None,
) -> List[Path]:
    """Dynamically discovers all state.vscdb paths across profiles and standard locations."""
    candidate_vscdbs_set = set()
    homes = [user_home] if user_home else [Path(os.path.expanduser("~"))]

    for h in homes:
        h_str = str(h)
        for pattern in [
            os.path.join(h_str, ".config", "*", "User", "globalStorage", "state.vscdb"),
            os.path.join(h_str, ".config", "Google", "*", "User", "globalStorage", "state.vscdb"),
            os.path.join(h_str, ".antigravity*", ".config", "*", "User", "globalStorage", "state.vscdb"),
            os.path.join(h_str, ".config", "*", "User", "workspaceStorage", "*", "state.vscdb"),
            os.path.join(h_str, ".config", "Google", "*", "User", "workspaceStorage", "*", "state.vscdb"),
            os.path.join(h_str, ".antigravity*", ".config", "*", "User", "workspaceStorage", "*", "state.vscdb"),
        ]:
            for vpath in glob.glob(pattern):
                if any(k in vpath.lower() for k in ["antigravity", "gemini"]):
                    candidate_vscdbs_set.add(Path(vpath).resolve())

    if ide_candidates:
        for cand in ide_candidates:
            cand_p = Path(cand)
            cand_vsc = cand_p / "User" / "globalStorage" / "state.vscdb"
            if cand_vsc.is_file():
                candidate_vscdbs_set.add(cand_vsc.resolve())
            for ws_vsc in glob.glob(str(cand_p / "User" / "workspaceStorage" / "*" / "state.vscdb")):
                candidate_vscdbs_set.add(Path(ws_vsc).resolve())

    return sorted(list(candidate_vscdbs_set))


def ingest_vscdb_summaries(
    candidate_vscdbs: List[Path],
    all_summaries: Dict[str, bytes],
    master_conv_dir: Path,
    con: sqlite3.Connection,
    pinned_set: Optional[Set[str]] = None,
    tombstones: Optional[Set[str]] = None,
) -> int:
    """
    Reads conversation titles from VS Code state.vscdb ItemTable and enriches
    any unassigned or generic conversation summaries, skipping tombstones.
    Returns:
        Number of conversations updated with authentic IDE titles.
    """
    ide_ingested_total = 0
    cur = con.cursor()

    for vscdb_p in candidate_vscdbs:
        if not vscdb_p.is_file():
            continue
        v_con = None
        try:
            v_con = sqlite3.connect(str(vscdb_p), timeout=15.0)
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
                    if tombstones and u_id in tombstones:
                        continue
                    raw = extract_pure_binary_summary(p_bin)
                    if not raw:
                        continue
                    parsed = parse_cascade_summary(raw)
                    if u_id in all_summaries:
                        curr_parsed = parse_cascade_summary(all_summaries[u_id])
                        curr_t = (curr_parsed.get("title") or curr_parsed.get("summary") or "").strip()
                        # Fast path: If master already has an authentic title, skip expensive prompt extraction
                        if curr_t and is_clean_title(curr_t) and curr_t not in ["Conversation", "Untitled Conversation"] and not any(k in curr_t for k in ["@[", " بعد از", "چطور"]):
                            continue

                    db_p = master_conv_dir / f"{u_id}.db"
                    tr_p = master_conv_dir.parent / "brain" / u_id / ".system_generated" / "logs" / "transcript.jsonl"
                    ide_summary = (parsed.get("summary") or "").strip()
                    ide_annot_title = (parsed.get("title") or "").strip()

                    # Prefer authentic summary (Tag 1), which holds LLM-generated title
                    # Tag 15 (title) is only user prompt fallback
                    ide_title = ""
                    for cand in [ide_summary, ide_annot_title]:
                        if (
                            cand
                            and is_clean_title(cand)
                            and not is_prompt_text(cand, clean_prompts)
                            and cand.strip() not in ["Conversation", "Untitled Conversation"]
                        ):
                            ide_title = cand.strip()
                            break

                    if u_id in all_summaries:
                        curr_parsed = parse_cascade_summary(all_summaries[u_id])
                        curr_t = (curr_parsed.get("title") or curr_parsed.get("summary") or "").strip()
                        should_update = False
                        if ide_title:
                            if (
                                not curr_t
                                or not is_clean_title(curr_t)
                                or is_prompt_text(curr_t, clean_prompts)
                                or curr_t in ["Conversation", "Untitled Conversation"]
                            ):
                                should_update = True

                        if should_update:
                            db_p = master_conv_dir / f"{u_id}.db"
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
                                u_id,
                                ide_title,
                                ide_title,
                                sc,
                                last_modified_iso=curr_parsed.get("last_modified_iso") or curr_parsed.get("ts_3"),
                                last_user_step=user_step,
                                workspace_uri=norm_ws,
                                project_id=effective_pid,
                                created_iso=curr_parsed.get("created_iso") or curr_parsed.get("ts_7"),
                                last_user_input_iso=curr_parsed.get("last_user_input_iso") or curr_parsed.get("ts_10"),
                                pinned=is_pin,
                                archived=is_arc,
                            )
                            all_summaries[u_id] = new_bin
                            cur.execute(
                                "UPDATE conversation_summaries SET title=?, raw_summary=? WHERE conversation_id=?",
                                (ide_title, new_bin, u_id),
                            )
                            sync_annotation_file(
                                master_conv_dir.parent,
                                u_id,
                                ide_title,
                                pinned=is_pin,
                                archived=is_arc,
                                force=True,
                            )
                            ide_ingested_total += 1
            con.commit()
        except Exception:
            pass
        finally:
            if v_con:
                try:
                    v_con.close()
                except Exception:
                    pass

    return ide_ingested_total


def write_vscdb_unified_state(
    candidate_vscdbs: List[Path],
    all_summaries: Dict[str, bytes],
) -> None:
    """
    Serializes and writes antigravityUnifiedStateSync, trajectorySummaries,
    and sidebarWorkspaces to ItemTable in all target state.vscdb files.
    """
    active_workspaces = set()
    for raw in all_summaries.values():
        try:
            parsed = parse_cascade_summary(raw)
            ws = parsed.get("workspace_uri")
            if ws and str(ws).startswith("file://") and is_valid_workspace_uri(str(ws)):
                norm_w = normalize_workspace_uri(str(ws))
                if norm_w and is_valid_workspace_uri(norm_w):
                    active_workspaces.add(str(norm_w))
        except Exception:
            pass

    for vscdb_p in candidate_vscdbs:
        if not vscdb_p.is_file():
            continue
        # Only write unified state to globalStorage/state.vscdb, skip workspace-scoped databases
        if "globalstorage" not in str(vscdb_p).lower():
            continue
        v_con = None
        try:
            v_con = sqlite3.connect(str(vscdb_p), timeout=15.0)
            v_cur = v_con.cursor()
            v_cur.execute("CREATE TABLE IF NOT EXISTS ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB);")
            old_sync_row = v_cur.execute(
                "SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync';"
            ).fetchone()
            old_sync_b64 = old_sync_row[0] if old_sync_row else None

            old_traj_row = v_cur.execute(
                "SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync.trajectorySummaries';"
            ).fetchone()
            old_traj_b64 = old_traj_row[0] if old_traj_row else None

            state_summaries = dict(all_summaries)
            if old_traj_b64:
                try:
                    existing_entries = extract_entries_from_proto(base64.b64decode(old_traj_b64))
                    for e_cid, e_bin in existing_entries.items():
                        e_raw = extract_pure_binary_summary(e_bin)
                        if e_raw:
                            e_parsed = parse_cascade_summary(e_raw)
                            e_sc = e_parsed.get("step_count", 0)
                            if e_cid in state_summaries:
                                curr_parsed = parse_cascade_summary(state_summaries[e_cid])
                                curr_sc = curr_parsed.get("step_count", 0)
                                if e_sc > curr_sc:
                                    # Preserve higher step count from active IDE session,
                                    # but retain validated workspace_uri and project_id from state_summaries
                                    valid_ws = curr_parsed.get("workspace_uri") if is_valid_workspace_uri(curr_parsed.get("workspace_uri")) else None
                                    if not valid_ws and is_valid_workspace_uri(e_parsed.get("workspace_uri")):
                                        valid_ws = e_parsed.get("workspace_uri")
                                    valid_pid = curr_parsed.get("project_id") or e_parsed.get("project_id")
                                    state_summaries[e_cid] = build_cascade_summary(
                                        e_cid,
                                        curr_parsed.get("title") or e_parsed.get("title", ""),
                                        curr_parsed.get("summary") or e_parsed.get("summary", ""),
                                        e_sc,
                                        last_modified_iso=e_parsed.get("last_modified_iso") or curr_parsed.get("last_modified_iso"),
                                        last_user_step=e_parsed.get("last_user_step") or curr_parsed.get("last_user_step", -1),
                                        workspace_uri=valid_ws,
                                        project_id=valid_pid,
                                        created_iso=curr_parsed.get("created_iso") or e_parsed.get("created_iso"),
                                        last_user_input_iso=e_parsed.get("last_user_input_iso") or curr_parsed.get("last_user_input_iso"),
                                        pinned=curr_parsed.get("pinned", False),
                                        archived=curr_parsed.get("archived", False),
                                    )
                            else:
                                if is_valid_workspace_uri(e_parsed.get("workspace_uri")):
                                    state_summaries[e_cid] = e_raw
                                else:
                                    state_summaries[e_cid] = build_cascade_summary(
                                        e_cid,
                                        e_parsed.get("title", ""),
                                        e_parsed.get("summary", ""),
                                        e_sc,
                                        last_modified_iso=e_parsed.get("last_modified_iso"),
                                        last_user_step=e_parsed.get("last_user_step", -1),
                                        workspace_uri=None,
                                        project_id=e_parsed.get("project_id"),
                                        created_iso=e_parsed.get("created_iso"),
                                        last_user_input_iso=e_parsed.get("last_user_input_iso"),
                                        pinned=e_parsed.get("pinned", False),
                                        archived=e_parsed.get("archived", False),
                                    )
                except Exception:
                    pass

            val_wrap_b64 = build_summaries_state(state_summaries)
            outer_b64 = build_unified_state_sync(state_summaries, existing_raw_b64=old_sync_b64)

            # Ensure sidebarWorkspaces includes all active workspaces
            old_ws_row = v_cur.execute(
                "SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync.sidebarWorkspaces';"
            ).fetchone()
            old_ws_b64 = old_ws_row[0] if old_ws_row else None
            new_ws_b64 = update_sidebar_workspaces_state(old_ws_b64, sorted(list(active_workspaces)))

            # Fast path: Skip expensive disk writes if state payload is completely identical
            if outer_b64 == old_sync_b64 and val_wrap_b64 == old_traj_b64 and new_ws_b64 == old_ws_b64:
                continue

            v_cur.execute(
                "INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync.trajectorySummaries', ?);",
                (val_wrap_b64,),
            )
            v_cur.execute(
                "INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync', ?);",
                (outer_b64,),
            )
            v_cur.execute(
                "INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync.sidebarWorkspaces', ?);",
                (new_ws_b64,),
            )

            v_con.commit()
        except Exception:
            pass
        finally:
            if v_con:
                try:
                    v_con.close()
                except Exception:
                    pass
