"""
SQLite Schema Setup and Safe Database Copying.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Union


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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_conversation_summaries_last_user_input_time ON conversation_summaries (last_user_input_time);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_conversation_summaries_last_modified_time ON conversation_summaries (last_modified_time);")

    try:
        cur.execute("PRAGMA table_info(conversation_summaries);")
        cols = {row[1] for row in cur.fetchall()}
        if "workspace_uris" not in cols:
            cur.execute('ALTER TABLE conversation_summaries ADD COLUMN workspace_uris text NOT NULL DEFAULT "";')
        if "project_id" not in cols:
            cur.execute('ALTER TABLE conversation_summaries ADD COLUMN project_id text NOT NULL DEFAULT "";')
    except Exception:
        pass
    conn.commit()


def copy_sqlite_db_safely(src_path: Union[str, Path], dst_path: Union[str, Path]) -> bool:
    """Safely copies a SQLite database using the SQLite backup API, flushing WAL pages."""
    src_str, dst_str = str(src_path), str(dst_path)
    try:
        with sqlite3.connect(f"file:{src_str}?mode=ro", uri=True, timeout=10.0) as s_conn:
            with sqlite3.connect(dst_str, timeout=10.0) as d_conn:
                s_conn.backup(d_conn)
        st = os.stat(src_str)
        os.utime(dst_str, (st.st_atime, st.st_mtime))
        return True
    except Exception:
        try:
            shutil.copy2(src_str, dst_str)
            for sidecar in ["-wal", "-shm"]:
                side_src, side_dst = src_str + sidecar, dst_str + sidecar
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
