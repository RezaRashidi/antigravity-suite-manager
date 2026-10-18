"""
IDE state.vscdb Conversation Discovery and Purge Operations.
"""

from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path
from typing import List, Set, Union

from antigravity_suite.proto.vscdb import build_summaries_state, build_unified_state_sync
from antigravity_suite.proto.wire import extract_entries_from_proto, extract_pure_binary_summary


def get_active_ide_ids(candidate_vscdbs: List[Union[Path, str]]) -> Set[str]:
    """Extracts all conversation IDs currently active in IDE state.vscdb storage."""
    ide_ids: Set[str] = set()
    for vscdb in candidate_vscdbs:
        vscdb_p = Path(vscdb)
        if not vscdb_p.is_file():
            continue
        try:
            with sqlite3.connect(str(vscdb_p), timeout=5.0) as conn:
                for r in conn.cursor().execute(
                    "SELECT value FROM ItemTable WHERE key IN ('antigravityUnifiedStateSync.trajectorySummaries', 'antigravityUnifiedStateSync');"
                ).fetchall():
                    if r and r[0]:
                        try:
                            ide_ids.update(extract_entries_from_proto(base64.b64decode(r[0])).keys())
                        except Exception:
                            pass
        except Exception:
            pass
    return ide_ids


def purge_conversation_from_vscdb(vscdb_path: Path, conv_id: str) -> bool:
    """Removes a conversation UUID from a state.vscdb database (ItemTable)."""
    if not vscdb_path.is_file():
        return False
    modified = False
    try:
        with sqlite3.connect(str(vscdb_path), timeout=5.0) as conn:
            cur = conn.cursor()
            for key in ["antigravityUnifiedStateSync.trajectorySummaries", "antigravityUnifiedStateSync"]:
                row = cur.execute("SELECT value FROM ItemTable WHERE key = ?;", (key,)).fetchone()
                if row and row[0]:
                    try:
                        entries = extract_entries_from_proto(base64.b64decode(row[0]))
                        if conv_id in entries:
                            entries.pop(conv_id, None)
                            valid_sums = {uid: raw for uid, raw in ((u, extract_pure_binary_summary(p)) for u, p in entries.items()) if raw}
                            new_b64 = build_summaries_state(valid_sums) if key.endswith("trajectorySummaries") else build_unified_state_sync(valid_sums, existing_raw_b64=row[0])
                            cur.execute("UPDATE ItemTable SET value = ? WHERE key = ?;", (new_b64, key))
                            modified = True
                    except Exception:
                        pass

            row_g = cur.execute("SELECT value FROM ItemTable WHERE key = 'google.antigravity';").fetchone()
            if row_g and row_g[0]:
                try:
                    g_data = json.loads(row_g[0])
                    w_map = g_data.get("antigravity.workspaceCascadeMap", {})
                    if any(cid == conv_id for cid in w_map.values()):
                        g_data["antigravity.workspaceCascadeMap"] = {w: c for w, c in w_map.items() if c != conv_id}
                        cur.execute("UPDATE ItemTable SET value = ? WHERE key = 'google.antigravity';", (json.dumps(g_data),))
                        modified = True
                except Exception:
                    pass

            for nr in cur.execute("SELECT key FROM ItemTable WHERE key LIKE ?;", (f"%{conv_id}%",)).fetchall():
                if nr and nr[0]:
                    cur.execute("DELETE FROM ItemTable WHERE key = ?;", (nr[0],))
                    modified = True

            if modified:
                conn.commit()
    except Exception:
        pass
    return modified
