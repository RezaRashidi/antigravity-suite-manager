"""
Database Completeness Verification and Cache Management.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Dict, Tuple, Union

from antigravity_suite.proto.wire import read_varint

_VERIFIED_COMPLETE_DBS: Dict[str, Tuple[float, int]] = {}


def has_tag_in_proto(data: bytes, target_tag: int, target_wire: int = 2) -> bool:
    """Checks whether a valid protobuf tag exists at the top level of serialized bytes."""
    if not data:
        return False
    pos, d_len = 0, len(data)
    while pos < d_len:
        try:
            tag_wire, pos = read_varint(data, pos)
            wire_type, tag_num = tag_wire & 7, tag_wire >> 3
            if wire_type == 0:
                _, pos = read_varint(data, pos)
            elif wire_type == 1:
                pos += 8
            elif wire_type == 5:
                pos += 4
            elif wire_type == 2:
                length, pos = read_varint(data, pos)
                if pos + length > d_len:
                    break
                if tag_num == target_tag and wire_type == target_wire and length > 0:
                    return True
                pos += length
            else:
                break
        except Exception:
            break
    return False


def clear_synthesized_db_cache() -> None:
    """Clears the verified complete database cache."""
    _VERIFIED_COMPLETE_DBS.clear()


def is_synthesized_db_incomplete(db_path: Union[str, Path]) -> bool:
    """Checks if a conversation SQLite database has missing/empty message payloads."""
    from antigravity_suite.history.synthesizer_prompt import parse_step14_user_prompt

    db_p = str(db_path)
    try:
        st = os.stat(db_p)
    except Exception:
        return True
    mtime, size = st.st_mtime, st.st_size
    if size == 0:
        return True

    cached = _VERIFIED_COMPLETE_DBS.get(db_p)
    if cached is not None and cached[0] == mtime and cached[1] == size:
        return False

    try:
        with sqlite3.connect(db_p, timeout=15.0) as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM steps;")
            if cur.fetchone()[0] == 0:
                return True
            cur.execute("SELECT DISTINCT step_type FROM steps;")
            if {r[0] for r in cur.fetchall()} - {0, 14, 15, 132}:
                _VERIFIED_COMPLETE_DBS[db_p] = (mtime, size)
                return False
            cur.execute("SELECT step_payload FROM steps WHERE step_type = 14 LIMIT 5;")
            s14 = cur.fetchall()
            if s14 and not any(row[0] and bool(parse_step14_user_prompt(row[0])) for row in s14):
                return True
            cur.execute("SELECT step_payload FROM steps WHERE step_type = 15 LIMIT 5;")
            s15 = cur.fetchall()
            if s15 and not any(row[0] and has_tag_in_proto(row[0], 20, 2) for row in s15):
                return True
            cur.execute("SELECT metadata, step_payload FROM steps WHERE step_type = 132 LIMIT 5;")
            s132 = cur.fetchall()
            if s132 and not (any(r[0] and has_tag_in_proto(r[0], 4, 2) for r in s132) and any(r[1] and has_tag_in_proto(r[1], 140, 2) for r in s132)):
                return True
            cur.execute("SELECT metadata FROM steps WHERE metadata IS NOT NULL LIMIT 5;")
            sm = cur.fetchall()
            if sm and not any(r[0] and (has_tag_in_proto(r[0], 7, 2) or has_tag_in_proto(r[0], 1, 2)) for r in sm):
                return True
        _VERIFIED_COMPLETE_DBS[db_p] = (mtime, size)
        return False
    except Exception:
        return True
