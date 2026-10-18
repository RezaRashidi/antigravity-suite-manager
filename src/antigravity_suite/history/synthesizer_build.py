"""
Full SQLite Conversation Database Synthesizer from Transcript Logs.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from antigravity_suite.config import get_user_home
from antigravity_suite.history.synthesizer_classify import classify_transcript_step
from antigravity_suite.history.synthesizer_payloads import build_step14_payload, build_step15_payload, build_step132_payload, build_step_meta
from antigravity_suite.history.synthesizer_workspace import extract_workspace_from_transcript
from antigravity_suite.proto.trajectory import build_trajectory_metadata_blob


def _create_synth_tables(cur: sqlite3.Cursor, conv_id: str, ws_blob: bytes) -> None:
    for ddl in [
        "CREATE TABLE IF NOT EXISTS `trajectory_meta` (`trajectory_id` text, `cascade_id` text, `trajectory_type` integer, `source` integer, PRIMARY KEY (`trajectory_id`));",
        "CREATE TABLE IF NOT EXISTS `steps` (`idx` integer, `step_type` integer NOT NULL DEFAULT 0, `status` integer NOT NULL DEFAULT 0, `has_subtrajectory` numeric NOT NULL DEFAULT false, `metadata` blob, `error_details` blob, `permissions` blob, `task_details` blob, `render_info` blob, `step_payload` blob, `step_format` integer NOT NULL DEFAULT 0, PRIMARY KEY (`idx`));",
        "CREATE TABLE IF NOT EXISTS `gen_metadata` (`idx` integer, `data` blob, `size` integer NOT NULL DEFAULT 0, PRIMARY KEY (`idx`));",
        "CREATE TABLE IF NOT EXISTS `executor_metadata` (`idx` integer, `data` blob, PRIMARY KEY (`idx`));",
        "CREATE TABLE IF NOT EXISTS `parent_references` (`idx` integer, `data` blob, PRIMARY KEY (`idx`));",
        "CREATE TABLE IF NOT EXISTS `trajectory_metadata_blob` (`id` text DEFAULT 'main', `data` blob, PRIMARY KEY (`id`));",
        "CREATE TABLE IF NOT EXISTS `battle_mode_infos` (`idx` integer, `data` blob, PRIMARY KEY (`idx`));",
    ]:
        cur.execute(ddl)
    cur.execute("INSERT OR REPLACE INTO trajectory_meta VALUES (?, ?, 4, 1);", (conv_id, conv_id))
    cur.execute("INSERT OR REPLACE INTO trajectory_metadata_blob VALUES ('main', ?);", (ws_blob,))


def synthesize_db_from_transcript(
    conv_id: str,
    db_path: Union[str, Path],
    transcript_path: Union[str, Path],
    workspace_uri: Optional[str] = None,
    project_id: Optional[str] = None,
) -> bool:
    """Synthesizes a valid SQLite conversation database from transcript JSON lines with Protobuf payloads."""
    tf_str = str(transcript_path)
    if tf_str.endswith("transcript.jsonl") and os.path.isfile(tf_str.replace("transcript.jsonl", "transcript_full.jsonl")):
        tf_str = tf_str.replace("transcript.jsonl", "transcript_full.jsonl")
    if not os.path.isfile(tf_str):
        return False

    db_str = str(db_path)
    try:
        os.makedirs(os.path.dirname(db_str), exist_ok=True)
        with sqlite3.connect(db_str, timeout=15.0) as conn:
            cur = conn.cursor()
            ws_uri = workspace_uri or extract_workspace_from_transcript(tf_str, project_id=project_id, user_home=get_user_home())
            _create_synth_tables(cur, conv_id, build_trajectory_metadata_blob(conv_id, ws_uri, project_id))

            pending_tool_calls: List[Dict[str, Any]] = []
            steps_rows: List[Tuple[int, int, int, bytes, bytes]] = []
            out_idx = 0
            base_meta = build_step_meta(conv_id)

            with open(tf_str, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                    except Exception:
                        continue
                    classified = classify_transcript_step(entry)
                    if not classified:
                        continue
                    step_type, status = classified
                    content, thinking = entry.get("content", ""), entry.get("thinking", "")
                    tool_calls = entry.get("tool_calls", [])

                    if step_type == 14:
                        pending_tool_calls.clear()
                        meta, payload = bytes(base_meta), build_step14_payload(base_meta, status, content)
                    elif step_type == 15:
                        meta, payload = bytes(base_meta), build_step15_payload(base_meta, status, content, thinking, tool_calls, out_idx, pending_tool_calls)
                    else:
                        meta, payload = build_step132_payload(base_meta, status, content, str(entry.get("type", "")), out_idx, pending_tool_calls)

                    steps_rows.append((out_idx, step_type, status, meta, payload))
                    out_idx += 1

            if steps_rows:
                cur.execute("DELETE FROM steps;")
                cur.executemany("INSERT OR REPLACE INTO steps (idx, step_type, status, metadata, step_payload) VALUES (?, ?, ?, ?, ?);", steps_rows)
                conn.commit()
                return True
        return False
    except Exception:
        return False
