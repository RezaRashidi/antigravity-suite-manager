"""
SQLite Full-Text Search (FTS) Index Synchronization and Timestamp Repair.
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path
from typing import Optional


def _parse_nanos(iso_str: Optional[str]) -> int:
    if iso_str and not str(iso_str).startswith("0001"):
        try:
            dt = datetime.datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
            if dt.year > 2000:
                return int(dt.timestamp() * 1e9)
        except Exception:
            pass
    return int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1e9)


def sync_conversations_fts(
    conn: sqlite3.Connection, conv_id: str, title: str,
    workspace_uri: Optional[str], project_id: Optional[str],
    last_modified_iso: str, step_count: int, archived: bool = False,
) -> None:
    """Synchronizes header row (chunk_index = -1) in conversations_fts with nanosecond timestamp."""
    cur = conn.cursor()
    try:
        if not cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='conversations_fts';").fetchone():
            return
        nanos = _parse_nanos(last_modified_iso)
        ws_name = ""
        if workspace_uri:
            try:
                w_u = json.loads(str(workspace_uri))[0] if str(workspace_uri).startswith("[") else str(workspace_uri)
                ws_name = Path(w_u.replace("file://", "")).name
            except Exception:
                pass
        proj = project_id or ""
        row = cur.execute("SELECT rowid FROM conversations_fts WHERE conversation_id = ? AND chunk_index = -1;", (conv_id,)).fetchone()
        if row:
            cur.execute("""
                UPDATE conversations_fts
                SET last_modified_time = ?, step_count = ?, last_step_created_at = ?, title = ?, workspace = ?, project = ?, archived = ?
                WHERE rowid = ?;
            """, (nanos, step_count, nanos, title or "", ws_name, proj, 1 if archived else 0, row[0]))
        else:
            cur.execute("""
                INSERT INTO conversations_fts (
                    conversation_id, chunk_index, chunk_first_step, chunk_last_step,
                    last_modified_time, step_count, last_step_created_at, archived,
                    user_step_byte_offsets, agent_step_byte_offsets, title, workspace, project,
                    user_body, agent_body
                ) VALUES (?, -1, 0, 0, ?, ?, ?, ?, '', '', ?, ?, ?, '', '');
            """, (conv_id, nanos, step_count, nanos, 1 if archived else 0, title or "", ws_name, proj))
    except Exception:
        pass


def repair_fts_zero_timestamps(conn: sqlite3.Connection) -> int:
    """Repairs zero/null timestamps in conversations_fts header rows."""
    cur = conn.cursor()
    try:
        if not cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='conversations_fts';").fetchone():
            return 0
        rows = cur.execute("SELECT rowid, conversation_id, step_count FROM conversations_fts WHERE chunk_index = -1 AND (last_modified_time <= 0 OR last_modified_time IS NULL);").fetchall()
        if not rows:
            return 0
        repaired = 0
        for rowid, cid, sc in rows:
            s_row = cur.execute("SELECT last_modified_time, step_count FROM conversation_summaries WHERE conversation_id = ?;", (cid,)).fetchone()
            nanos = _parse_nanos(s_row[0] if s_row else None)
            step_cnt = max(sc or 0, s_row[1] if (s_row and s_row[1]) else 0)
            cur.execute("UPDATE conversations_fts SET last_modified_time = ?, last_step_created_at = ?, step_count = ? WHERE rowid = ?;", (nanos, nanos, step_cnt, rowid))
            repaired += 1
        if repaired > 0:
            conn.commit()
        return repaired
    except Exception:
        return 0
