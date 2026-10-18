"""
SQLite Summary Row Upsert Operations.
"""

from __future__ import annotations

import sqlite3

from antigravity_suite.history.models import ConversationSummary
from antigravity_suite.history.sqlite_fts import sync_conversations_fts


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
        last_modified_time = CASE
            WHEN excluded.last_modified_time != '' AND excluded.last_modified_time > '1980-01-01' THEN excluded.last_modified_time
            WHEN conversation_summaries.last_modified_time != '' AND conversation_summaries.last_modified_time > '1980-01-01' THEN conversation_summaries.last_modified_time
            ELSE strftime('%Y-%m-%d %H:%M:%S.000000+00:00', 'now')
        END,
        workspace_uris = CASE WHEN excluded.workspace_uris != '' THEN excluded.workspace_uris ELSE conversation_summaries.workspace_uris END,
        project_id = CASE
            WHEN excluded.project_id != '' AND excluded.project_id != 'outside-of-project' THEN excluded.project_id
            WHEN conversation_summaries.project_id = '' OR conversation_summaries.project_id IS NULL THEN excluded.project_id
            ELSE conversation_summaries.project_id
        END,
        last_user_input_time = CASE
            WHEN excluded.last_user_input_time != '' AND excluded.last_user_input_time > '1980-01-01' THEN excluded.last_user_input_time
            WHEN conversation_summaries.last_user_input_time != '' AND conversation_summaries.last_user_input_time > '1980-01-01' THEN conversation_summaries.last_user_input_time
            ELSE strftime('%Y-%m-%d %H:%M:%S.000000+00:00', 'now')
        END,
        last_user_input_step_index = CASE WHEN excluded.last_user_input_step_index >= 0 THEN excluded.last_user_input_step_index ELSE conversation_summaries.last_user_input_step_index END,
        raw_summary = CASE WHEN excluded.raw_summary IS NOT NULL THEN excluded.raw_summary ELSE conversation_summaries.raw_summary END,
        source = CASE
            WHEN conversation_summaries.source = 'CORTEX_TRAJECTORY_SOURCE_CASCADE_CLIENT' THEN ''
            WHEN excluded.source != '' AND excluded.source != 'CORTEX_TRAJECTORY_SOURCE_CASCADE_CLIENT' THEN excluded.source
            ELSE conversation_summaries.source
        END,
        app_data_dir = CASE
            WHEN excluded.app_data_dir != '' THEN excluded.app_data_dir
            ELSE conversation_summaries.app_data_dir
        END;""", (
        summary.conversation_id, summary.title, summary.preview, summary.step_count,
        summary.last_modified_time, summary.workspace_uris, summary.status, summary.source,
        summary.project_id, summary.agent_name, summary.parent_conversation_id,
        summary.nesting_depth, summary.battle_id, summary.winning_conversation_id,
        summary.not_fully_idle, summary.killed, summary.last_user_input_time,
        summary.last_user_input_step_index, summary.app_data_dir, summary.raw_summary, summary.group_id,
    ))

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
