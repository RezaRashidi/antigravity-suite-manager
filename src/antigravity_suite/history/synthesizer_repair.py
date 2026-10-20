"""
Database Step Gap Detection and Backfill Repair Engine.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import List, Tuple, Union

from antigravity_suite.history.synthesizer_classify import classify_transcript_step
from antigravity_suite.history.synthesizer_payloads import (
    build_step14_payload,
    build_step15_payload,
    build_step132_payload,
    build_step_meta,
)


def repair_database_step_gaps(
    db_path: Union[str, Path],
    transcript_path: Union[str, Path],
) -> int:
    """Detects and repairs missing step index gaps in a conversation SQLite database."""
    db_p, tf_str = str(db_path), str(transcript_path)
    if not os.path.isfile(db_p) or not os.path.isfile(tf_str):
        return 0
    if tf_str.endswith("transcript.jsonl") and os.path.isfile(tf_str.replace("transcript.jsonl", "transcript_full.jsonl")):
        tf_str = tf_str.replace("transcript.jsonl", "transcript_full.jsonl")

    try:
        with sqlite3.connect(db_p, timeout=15.0) as conn:
            cur = conn.cursor()
            existing_indices = set(r[0] for r in cur.execute("SELECT idx FROM steps;").fetchall())
            if not existing_indices:
                return 0
            missing_indices = set(range(max(existing_indices) + 1)) - existing_indices
            if not missing_indices:
                return 0

            conv_id = Path(db_p).stem
            rows_to_insert: List[Tuple[int, int, int, bytes, bytes]] = []

            with open(tf_str, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                    except Exception:
                        continue
                    step_idx = entry.get("step_index")
                    if step_idx is None or step_idx not in missing_indices:
                        continue
                    classified = classify_transcript_step(entry)
                    if not classified:
                        continue
                    step_type, status = classified
                    content, thinking = entry.get("content", ""), entry.get("thinking", "")
                    tool_calls = entry.get("tool_calls", [])
                    step_meta = build_step_meta(conv_id, entry.get("created_at"))

                    if step_type == 14:
                        meta, payload = bytes(step_meta), build_step14_payload(step_meta, status, content)
                    elif step_type == 15:
                        meta, payload = bytes(step_meta), build_step15_payload(step_meta, status, content, thinking, tool_calls, step_idx, [])
                    else:
                        meta, payload = build_step132_payload(step_meta, status, content, str(entry.get("type", "")), step_idx, [])

                    rows_to_insert.append((step_idx, step_type, status, meta, payload))

            if rows_to_insert:
                cur.executemany("INSERT OR IGNORE INTO steps (idx, step_type, status, metadata, step_payload) VALUES (?, ?, ?, ?, ?);", rows_to_insert)
                conn.commit()
                return len(rows_to_insert)
        return 0
    except Exception:
        return 0
