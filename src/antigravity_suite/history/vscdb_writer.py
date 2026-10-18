"""
Writing Unified State and Active Workspaces to IDE state.vscdb.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List

from antigravity_suite.history.projects import is_valid_workspace_uri, normalize_workspace_uri
from antigravity_suite.history.vscdb_state_builder import build_unified_payloads, merge_ide_active_state
from antigravity_suite.proto.cascade import parse_cascade_summary
from antigravity_suite.proto.vscdb import update_sidebar_workspaces_state


def write_vscdb_unified_state(
    candidate_vscdbs: List[Path],
    all_summaries: Dict[str, bytes],
) -> None:
    """Serializes and writes unified state and sidebar workspaces to IDE state.vscdb files."""
    active_workspaces = set()
    for raw in all_summaries.values():
        try:
            ws = parse_cascade_summary(raw).get("workspace_uri")
            if ws and str(ws).startswith("file://") and is_valid_workspace_uri(str(ws)):
                norm_w = normalize_workspace_uri(str(ws))
                if norm_w and is_valid_workspace_uri(norm_w):
                    active_workspaces.add(str(norm_w))
        except Exception:
            pass

    for vscdb_p in candidate_vscdbs:
        if not vscdb_p.is_file() or "globalstorage" not in str(vscdb_p).lower():
            continue
        try:
            with sqlite3.connect(str(vscdb_p), timeout=15.0) as v_con:
                v_cur = v_con.cursor()
                v_cur.execute("CREATE TABLE IF NOT EXISTS ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB);")

                old_sync_row = v_cur.execute("SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync';").fetchone()
                old_sync_b64 = old_sync_row[0] if old_sync_row else None

                old_traj_row = v_cur.execute("SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync.trajectorySummaries';").fetchone()
                old_traj_b64 = old_traj_row[0] if old_traj_row else None

                old_ws_row = v_cur.execute("SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync.sidebarWorkspaces';").fetchone()
                old_ws_b64 = old_ws_row[0] if old_ws_row else None

                state_summaries = merge_ide_active_state(all_summaries, old_traj_b64)
                val_wrap_b64, outer_b64 = build_unified_payloads(state_summaries, old_sync_b64)
                new_ws_b64 = update_sidebar_workspaces_state(old_ws_b64, sorted(list(active_workspaces)))

                if outer_b64 == old_sync_b64 and val_wrap_b64 == old_traj_b64 and new_ws_b64 == old_ws_b64:
                    continue

                v_cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync.trajectorySummaries', ?);", (val_wrap_b64,))
                v_cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync', ?);", (outer_b64,))
                v_cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync.sidebarWorkspaces', ?);", (new_ws_b64,))
                v_con.commit()
        except Exception:
            pass
