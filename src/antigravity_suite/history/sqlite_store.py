"""
SQLite Storage Adapter for conversation_summaries.db and Conversation Trajectories.

Handles schema migrations, transactional upserts, step counting, and index integrity.
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from antigravity_suite.history.models import ConversationSummary



def ensure_summaries_schema(conn: sqlite3.Connection) -> None:
    """Ensures conversation_summaries table exists with all standard columns and WAL mode enabled."""
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA journal_mode = WAL;")
        cur.execute("PRAGMA synchronous = NORMAL;")
        cur.execute("PRAGMA busy_timeout = 5000;")
    except Exception:
        pass

    cur.execute("""CREATE TABLE IF NOT EXISTS conversation_summaries (
        conversation_id text PRIMARY KEY,
        title text NOT NULL DEFAULT "",
        preview text NOT NULL DEFAULT "",
        step_count integer NOT NULL DEFAULT 0,
        last_modified_time datetime NOT NULL,
        workspace_uris text NOT NULL DEFAULT "",
        status text NOT NULL DEFAULT "CASCADE_RUN_STATUS_IDLE",
        source text NOT NULL DEFAULT "",
        project_id text NOT NULL DEFAULT "",
        agent_name text NOT NULL DEFAULT "",
        parent_conversation_id text NOT NULL DEFAULT "",
        nesting_depth integer NOT NULL DEFAULT 0,
        battle_id text NOT NULL DEFAULT "",
        winning_conversation_id text NOT NULL DEFAULT "",
        not_fully_idle numeric NOT NULL DEFAULT false,
        killed numeric NOT NULL DEFAULT false,
        last_user_input_time datetime NOT NULL,
        last_user_input_step_index integer NOT NULL DEFAULT -1,
        app_data_dir text NOT NULL DEFAULT "antigravity",
        raw_summary blob,
        group_id text NOT NULL DEFAULT ""
    );""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_conversation_summaries_last_user_input_time
        ON conversation_summaries (last_user_input_time);""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_conversation_summaries_last_modified_time
        ON conversation_summaries (last_modified_time);""")

    # Ensure legacy schemas have workspace_uris and project_id columns
    try:
        cur.execute("PRAGMA table_info(conversation_summaries);")
        cols = {row[1] for row in cur.fetchall()}
        if "workspace_uris" not in cols:
            cur.execute('ALTER TABLE conversation_summaries ADD COLUMN workspace_uris text NOT NULL DEFAULT "";')
        if "project_id" not in cols:
            cur.execute('ALTER TABLE conversation_summaries ADD COLUMN project_id text NOT NULL DEFAULT "";')
    except Exception:
        pass

    try:
        repair_fts_zero_timestamps(conn)
    except Exception:
        pass

    conn.commit()


def copy_sqlite_db_safely(src_path: Union[str, Path], dst_path: Union[str, Path]) -> bool:
    """Safely copies a SQLite database using the SQLite backup API, flushing WAL pages."""
    src_str = str(src_path)
    dst_str = str(dst_path)
    try:
        with sqlite3.connect(f"file:{src_str}?mode=ro", uri=True, timeout=10.0) as s_conn:
            with sqlite3.connect(dst_str, timeout=10.0) as d_conn:
                s_conn.backup(d_conn)
        try:
            st = os.stat(src_str)
            os.utime(dst_str, (st.st_atime, st.st_mtime))
        except Exception:
            pass
        return True
    except Exception:
        try:
            import shutil
            shutil.copy2(src_str, dst_str)
            for sidecar in ["-wal", "-shm"]:
                side_src = src_str + sidecar
                side_dst = dst_str + sidecar
                if os.path.exists(side_src):
                    shutil.copy2(side_src, side_dst)
                elif os.path.exists(side_dst):
                    try:
                        os.remove(side_dst)
                    except Exception:
                        pass
            return True
        except Exception:
            return False


def load_existing_summaries(
    db_path: Union[str, Path],
) -> Dict[str, Tuple[Any, ...]]:
    """
    Loads existing indexed summaries from conversation_summaries.db.
    Returns:
      conv_id -> (title, preview, step_count, last_modified_time, raw_summary, last_user_input_time, last_user_input_step_index)
    """
    db_str = str(db_path)
    if not os.path.isfile(db_str):
        return {}

    conn = None
    try:
        conn = sqlite3.connect(db_str, timeout=15.0)
        cur = conn.cursor()
        ensure_summaries_schema(conn)

        existing: Dict[str, Tuple[Any, ...]] = {}
        for r in cur.execute(
            "SELECT conversation_id, title, preview, step_count, last_modified_time, raw_summary, last_user_input_time, last_user_input_step_index, workspace_uris, project_id FROM conversation_summaries;"
        ).fetchall():
            existing[r[0]] = (r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9])
        return existing
    except Exception:
        return {}
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def sync_conversations_fts(
    conn: sqlite3.Connection,
    conv_id: str,
    title: str,
    workspace_uri: Optional[str],
    project_id: Optional[str],
    last_modified_iso: str,
    step_count: int,
    archived: bool = False,
) -> None:
    """Synchronizes header row (chunk_index = -1) in conversations_fts with authentic nanosecond timestamp."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='conversations_fts';")
        if not cur.fetchone():
            return

        nanos = 0
        if last_modified_iso:
            try:
                clean_iso = str(last_modified_iso).replace("Z", "+00:00")
                dt = datetime.datetime.fromisoformat(clean_iso)
                nanos = int(dt.timestamp() * 1e9)
            except Exception:
                nanos = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1e9)
        if nanos <= 0:
            nanos = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1e9)

        ws_name = ""
        if workspace_uri:
            try:
                if str(workspace_uri).startswith("["):
                    uris = json.loads(str(workspace_uri))
                    w_u = uris[0] if uris else ""
                else:
                    w_u = str(workspace_uri)
                ws_name = Path(w_u.replace("file://", "")).name
            except Exception:
                ws_name = ""

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


def upsert_summary(conn: sqlite3.Connection, summary: ConversationSummary) -> None:
    """Inserts or updates a conversation summary row preserving authentic metadata."""
    cur = conn.cursor()
    cur.execute("""INSERT INTO conversation_summaries (
        conversation_id, title, preview, step_count, last_modified_time,
        workspace_uris, status, source, project_id, agent_name,
        parent_conversation_id, nesting_depth, battle_id, winning_conversation_id,
        not_fully_idle, killed, last_user_input_time, last_user_input_step_index,
        app_data_dir, raw_summary, group_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(conversation_id) DO UPDATE SET
        title = CASE WHEN excluded.title != '' THEN excluded.title ELSE conversation_summaries.title END,
        preview = CASE WHEN excluded.preview != '' THEN excluded.preview ELSE conversation_summaries.preview END,
        step_count = CASE WHEN excluded.step_count > 0 THEN excluded.step_count ELSE conversation_summaries.step_count END,
        last_modified_time = CASE WHEN excluded.last_modified_time != '' THEN excluded.last_modified_time ELSE conversation_summaries.last_modified_time END,
        workspace_uris = CASE WHEN excluded.workspace_uris != '' THEN excluded.workspace_uris ELSE conversation_summaries.workspace_uris END,
        project_id = CASE
            WHEN excluded.project_id != '' AND excluded.project_id != 'outside-of-project' THEN excluded.project_id
            WHEN conversation_summaries.project_id = '' OR conversation_summaries.project_id IS NULL THEN excluded.project_id
            ELSE conversation_summaries.project_id
        END,
        last_user_input_time = CASE WHEN excluded.last_user_input_time != '' THEN excluded.last_user_input_time ELSE conversation_summaries.last_user_input_time END,
        last_user_input_step_index = CASE WHEN excluded.last_user_input_step_index >= 0 THEN excluded.last_user_input_step_index ELSE conversation_summaries.last_user_input_step_index END,
        raw_summary = CASE WHEN excluded.raw_summary IS NOT NULL THEN excluded.raw_summary ELSE conversation_summaries.raw_summary END,
        source = CASE
            WHEN conversation_summaries.source = 'CORTEX_TRAJECTORY_SOURCE_CASCADE_CLIENT' THEN ''
            WHEN excluded.source != '' AND excluded.source != 'CORTEX_TRAJECTORY_SOURCE_CASCADE_CLIENT' THEN excluded.source
            ELSE conversation_summaries.source
        END;""", (
        summary.conversation_id,
        summary.title,
        summary.preview,
        summary.step_count,
        summary.last_modified_time,
        summary.workspace_uris,
        summary.status,
        summary.source,
        summary.project_id,
        summary.agent_name,
        summary.parent_conversation_id,
        summary.nesting_depth,
        summary.battle_id,
        summary.winning_conversation_id,
        summary.not_fully_idle,
        summary.killed,
        summary.last_user_input_time,
        summary.last_user_input_step_index,
        summary.app_data_dir,
        summary.raw_summary,
        summary.group_id,
    ))

    # Synchronize FTS header index
    sync_conversations_fts(
        conn,
        conv_id=summary.conversation_id,
        title=summary.title,
        workspace_uri=summary.workspace_uris,
        project_id=summary.project_id,
        last_modified_iso=summary.last_modified_time,
        step_count=summary.step_count,
        archived=False,
    )


def repair_fts_zero_timestamps(conn: sqlite3.Connection) -> int:
    """
    Ensures all header rows (chunk_index = -1) in conversations_fts have authentic,
    non-zero nanosecond timestamps matching conversation_summaries or current time.
    Prevents conversations from being sorted to Year 0001 in the Desktop App sidebar.
    """
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='conversations_fts';")
        if not cur.fetchone():
            return 0

        rows = cur.execute("""
            SELECT rowid, conversation_id, title, workspace, project, step_count, archived
            FROM conversations_fts
            WHERE chunk_index = -1 AND (last_modified_time = 0 OR last_modified_time IS NULL);
        """).fetchall()

        if not rows:
            return 0

        repaired = 0
        for rowid, cid, title, ws, proj, sc, arch in rows:
            s_row = cur.execute(
                "SELECT last_modified_time, step_count FROM conversation_summaries WHERE conversation_id = ?;",
                (cid,)
            ).fetchone()
            nanos = 0
            step_cnt = sc or 0
            if s_row and s_row[0]:
                try:
                    clean_iso = str(s_row[0]).replace("Z", "+00:00")
                    dt = datetime.datetime.fromisoformat(clean_iso)
                    nanos = int(dt.timestamp() * 1e9)
                    if s_row[1] and s_row[1] > step_cnt:
                        step_cnt = s_row[1]
                except Exception:
                    pass
            if nanos <= 0:
                nanos = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1e9)

            cur.execute("""
                UPDATE conversations_fts
                SET last_modified_time = ?, last_step_created_at = ?, step_count = ?
                WHERE rowid = ?;
            """, (nanos, nanos, step_cnt, rowid))
            repaired += 1

        if repaired > 0:
            conn.commit()
        return repaired
    except Exception:
        return 0



_STEP_COUNT_CACHE: Dict[str, Tuple[float, int, int]] = {}  # db_str -> (mtime, size, count)


def clear_step_count_cache() -> None:
    """Clears the in-memory step count cache."""
    _STEP_COUNT_CACHE.clear()


def get_actual_steps_count(db_path: Union[str, Path]) -> int:
    """
    Returns the count of steps from a trajectory SQLite database.
    Uses compound stat caching (file_path, st_mtime, st_size) to eliminate redundant
    SQLite connection overhead on unchanged databases.
    """
    db_str = str(db_path)
    try:
        st = os.stat(db_str)
    except Exception:
        return 0

    mtime = st.st_mtime
    size = st.st_size
    if size == 0:
        return 0

    cached = _STEP_COUNT_CACHE.get(db_str)
    if cached is not None and cached[0] == mtime and cached[1] == size:
        return cached[2]

    conn = None
    try:
        conn = sqlite3.connect(db_str, timeout=15.0)
        cnt = int(conn.cursor().execute("SELECT count(*) FROM steps;").fetchone()[0])
        _STEP_COUNT_CACHE[db_str] = (mtime, size, cnt)
        return cnt
    except Exception:
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
