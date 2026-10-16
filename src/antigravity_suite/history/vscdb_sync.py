"""
VS Code Global Storage (state.vscdb) Synchronization Engine.

Extracts authentic conversation titles from IDE state.vscdb storage and mirrors
unified Protobuf state sync back to IDE globalStorage databases.
"""

from __future__ import annotations

import base64
import glob
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from antigravity_suite.history.sqlite_store import get_actual_steps_count
from antigravity_suite.proto.cascade import build_cascade_summary, get_last_user_step_index, parse_cascade_summary
from antigravity_suite.proto.trajectory import parse_trajectory_metadata_blob
from antigravity_suite.proto.vscdb import build_summaries_state, build_unified_state_sync
from antigravity_suite.proto.wire import extract_entries_from_proto, extract_pure_binary_summary


def get_db_trajectory_meta(db_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Reads workspace_uri and project_id from trajectory_metadata_blob if present."""
    if not db_path.is_file():
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
    homes = [user_home, Path(os.path.expanduser("~"))]

    for h in homes:
        h_str = str(h)
        for pattern in [
            os.path.join(h_str, ".config", "*", "User", "globalStorage", "state.vscdb"),
            os.path.join(h_str, ".config", "Google", "*", "User", "globalStorage", "state.vscdb"),
            os.path.join(h_str, ".antigravity*", ".config", "*", "User", "globalStorage", "state.vscdb"),
        ]:
            for vpath in glob.glob(pattern):
                if any(k in vpath.lower() for k in ["antigravity", "gemini"]):
                    candidate_vscdbs_set.add(Path(vpath).resolve())

    if ide_candidates:
        for cand in ide_candidates:
            cand_vsc = Path(cand) / "User" / "globalStorage" / "state.vscdb"
            if cand_vsc.is_file():
                candidate_vscdbs_set.add(cand_vsc.resolve())

    return sorted(list(candidate_vscdbs_set))


def ingest_vscdb_summaries(
    candidate_vscdbs: List[Path],
    all_summaries: Dict[str, bytes],
    master_conv_dir: Path,
    con: sqlite3.Connection,
) -> int:
    """
    Reads conversation titles from VS Code state.vscdb ItemTable and enriches
    any unassigned or generic conversation summaries.
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
                    raw = extract_pure_binary_summary(p_bin)
                    if not raw:
                        continue
                    parsed = parse_cascade_summary(raw)
                    ide_title = parsed.get("title") or parsed.get("summary")
                    if u_id in all_summaries:
                        curr_parsed = parse_cascade_summary(all_summaries[u_id])
                        curr_t = curr_parsed.get("title") or curr_parsed.get("summary")
                        if ide_title and (
                            not curr_t or curr_t in ["Conversation", "IDE Conversation", "Untitled Conversation"]
                        ):
                            db_p = master_conv_dir / f"{u_id}.db"
                            db_ws_uri, db_proj_id = get_db_trajectory_meta(db_p)
                            sc = max(get_actual_steps_count(db_p), curr_parsed.get("step_count", 0), curr_parsed.get(2, 0), 1)
                            user_step = get_last_user_step_index(db_p, sc)
                            new_bin = build_cascade_summary(
                                u_id,
                                ide_title,
                                ide_title,
                                sc,
                                last_user_step=user_step,
                                workspace_uri=db_ws_uri or curr_parsed.get("workspace_uri"),
                                project_id=db_proj_id or curr_parsed.get("project_id"),
                            )
                            all_summaries[u_id] = new_bin
                            cur.execute(
                                "UPDATE conversation_summaries SET title=?, raw_summary=? WHERE conversation_id=?",
                                (ide_title, new_bin, u_id),
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
    Serializes and writes antigravityUnifiedStateSync and trajectorySummaries
    to ItemTable in all target state.vscdb files preserving existing metadata.
    """
    for vscdb_p in candidate_vscdbs:
        if not vscdb_p.is_file():
            continue
        v_con = None
        try:
            v_con = sqlite3.connect(str(vscdb_p), timeout=15.0)
            v_cur = v_con.cursor()
            old_sync_row = v_cur.execute(
                "SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync';"
            ).fetchone()
            old_sync_b64 = old_sync_row[0] if old_sync_row else None

            val_wrap_b64 = build_summaries_state(all_summaries)
            outer_b64 = build_unified_state_sync(all_summaries, existing_raw_b64=old_sync_b64)

            v_cur.execute(
                "INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync.trajectorySummaries', ?);",
                (val_wrap_b64,),
            )
            v_cur.execute(
                "INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync', ?);",
                (outer_b64,),
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
