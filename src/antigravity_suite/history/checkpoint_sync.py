"""
Checkpoint Step (step_type = 23) Synchronization and Synthesis Engine.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Optional, Union

from antigravity_suite.history.extractor_checkpoint import parse_step23_checkpoint_title
from antigravity_suite.history.title_sanitizer import is_clean_title
from antigravity_suite.proto.wire_varint import encode_tag_bytes, encode_tag_uint


def build_step23_payload(step_meta_bytes: bytes, title: str, step_idx: int, prompt: str = "") -> bytes:
    """Builds Step 23 (CORTEX_STEP_TYPE_CHECKPOINT) Protobuf payload with authentic title."""
    tag30 = bytearray()
    tag30 += encode_tag_bytes(4, title.encode("utf-8", errors="ignore"))
    tag30 += encode_tag_uint(9, 1)
    tag30 += encode_tag_uint(12, step_idx)
    if prompt:
        tag30 += encode_tag_bytes(19, prompt.encode("utf-8", errors="ignore"))
    tag30 += encode_tag_uint(24, 1)
    tag30 += encode_tag_uint(25, 0)

    payload = bytearray()
    payload += encode_tag_uint(1, 23)
    payload += encode_tag_uint(4, 3)
    if step_meta_bytes:
        payload += encode_tag_bytes(5, step_meta_bytes)
    payload += encode_tag_bytes(30, bytes(tag30))
    return bytes(payload)


def ensure_db_checkpoint_title(
    db_path: Union[str, Path],
    conv_id: str,
    title: str,
    prompt: str = "",
    transcript_path: Optional[Union[str, Path]] = None,
    allow_fallback: bool = False,
) -> bool:
    """Ensures conversation SQLite database contains a step_type = 23 checkpoint reflecting authentic title."""
    if not title or not is_clean_title(title) or title in ["Conversation", "Untitled Conversation", "---"] or not os.path.isfile(str(db_path)):
        return False
    if not allow_fallback and (title.endswith(" Chat") or title.startswith("Desktop:")):
        return False
    try:
        with sqlite3.connect(str(db_path), timeout=15.0) as conn:
            cur = conn.cursor()
            cur.execute("SELECT idx, step_payload FROM steps WHERE step_type = 23;")
            existing_s23 = cur.fetchall()
            if existing_s23:
                last_idx, last_payload = existing_s23[-1]
                old_t = parse_step23_checkpoint_title(last_payload)
                if old_t == title:
                    return False
                if old_t and (title.endswith(" Chat") or not is_clean_title(title)):
                    return False
                cur.execute("SELECT metadata FROM steps WHERE idx = ?;", (last_idx,))
                meta_row = cur.fetchone()
                s_meta = meta_row[0] if meta_row and meta_row[0] else b""
                cur.execute("UPDATE steps SET step_payload = ? WHERE idx = ?;", (build_step23_payload(s_meta, title, last_idx, prompt), last_idx))
                conn.commit()
                return True

            cur.execute("SELECT max(idx) FROM steps;")
            max_r = cur.fetchone()
            next_idx = (max_r[0] if max_r and max_r[0] is not None else -1) + 1
            cur.execute("SELECT metadata FROM steps WHERE metadata IS NOT NULL ORDER BY idx DESC LIMIT 1;")
            m_row = cur.fetchone()
            s_meta = m_row[0] if m_row and m_row[0] else b""
            payload = build_step23_payload(s_meta, title, next_idx, prompt)
            cur.execute("INSERT INTO steps (idx, step_type, status, metadata, step_payload) VALUES (?, 23, 3, ?, ?);", (next_idx, s_meta, payload))
            conn.commit()
    except Exception:
        return False
    return True

