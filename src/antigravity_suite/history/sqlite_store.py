"""
SQLite Storage Adapter for conversation_summaries.db and Conversation Trajectories.

Handles schema migrations, transactional upserts, step counting, and index integrity.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from antigravity_suite.history.models import ConversationSummary


def ensure_summaries_schema(conn: sqlite3.Connection) -> None:
    """Ensures conversation_summaries table exists with all standard columns."""
    cur = conn.cursor()
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
    conn.commit()


def load_existing_summaries(
    db_path: Union[str, Path],
) -> Dict[str, Tuple[str, str, int, str, Optional[bytes]]]:
    """
    Loads existing indexed summaries from conversation_summaries.db.
    Returns:
      conv_id -> (title, preview, step_count, last_modified_time, raw_summary)
    """
    db_str = str(db_path)
    if not os.path.isfile(db_str):
        return {}

    conn = sqlite3.connect(db_str, timeout=15.0)
    cur = conn.cursor()
    ensure_summaries_schema(conn)

    existing: Dict[str, Tuple[str, str, int, str, Optional[bytes]]] = {}
    for r in cur.execute("SELECT conversation_id, title, preview, step_count, last_modified_time, raw_summary FROM conversation_summaries;").fetchall():
        existing[r[0]] = (r[1], r[2], r[3], r[4], r[5])
    conn.close()
    return existing


def upsert_summary(conn: sqlite3.Connection, summary: ConversationSummary) -> None:
    """Inserts or updates a conversation summary row preserving non-empty metadata."""
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
        last_modified_time = excluded.last_modified_time,
        workspace_uris = CASE WHEN excluded.workspace_uris != '' THEN excluded.workspace_uris ELSE conversation_summaries.workspace_uris END,
        status = CASE WHEN excluded.status != '' THEN excluded.status ELSE conversation_summaries.status END,
        source = CASE WHEN excluded.source != '' THEN excluded.source ELSE conversation_summaries.source END,
        project_id = CASE WHEN excluded.project_id != '' AND excluded.project_id != 'outside-of-project' THEN excluded.project_id ELSE conversation_summaries.project_id END,
        agent_name = CASE WHEN excluded.agent_name != '' THEN excluded.agent_name ELSE conversation_summaries.agent_name END,
        parent_conversation_id = CASE WHEN excluded.parent_conversation_id != '' THEN excluded.parent_conversation_id ELSE conversation_summaries.parent_conversation_id END,
        nesting_depth = CASE WHEN excluded.nesting_depth > 0 THEN excluded.nesting_depth ELSE conversation_summaries.nesting_depth END,
        battle_id = CASE WHEN excluded.battle_id != '' THEN excluded.battle_id ELSE conversation_summaries.battle_id END,
        winning_conversation_id = CASE WHEN excluded.winning_conversation_id != '' THEN excluded.winning_conversation_id ELSE conversation_summaries.winning_conversation_id END,
        not_fully_idle = excluded.not_fully_idle,
        killed = excluded.killed,
        last_user_input_time = excluded.last_user_input_time,
        last_user_input_step_index = CASE WHEN excluded.last_user_input_step_index >= 0 THEN excluded.last_user_input_step_index ELSE conversation_summaries.last_user_input_step_index END,
        app_data_dir = CASE WHEN excluded.app_data_dir != '' THEN excluded.app_data_dir ELSE conversation_summaries.app_data_dir END,
        raw_summary = CASE WHEN excluded.raw_summary IS NOT NULL THEN excluded.raw_summary ELSE conversation_summaries.raw_summary END,
        group_id = CASE WHEN excluded.group_id != '' THEN excluded.group_id ELSE conversation_summaries.group_id END;""", (
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


def get_actual_steps_count(db_path: Union[str, Path]) -> int:
    """Returns the count of steps from a trajectory SQLite database."""
    db_str = str(db_path)
    if not os.path.isfile(db_str):
        return 0
    try:
        conn = sqlite3.connect(db_str, timeout=15.0)
        cnt = conn.cursor().execute("SELECT count(*) FROM steps;").fetchone()[0]
        conn.close()
        return int(cnt)
    except Exception:
        return 0
