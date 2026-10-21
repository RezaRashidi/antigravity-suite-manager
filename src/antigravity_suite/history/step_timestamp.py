"""
Fallback Authentic Timestamp Extractor for Legacy Conversations.

Extracts authentic timestamps from SQLite steps metadata or brain directory mtime.
"""

from __future__ import annotations

import datetime
import os
import sqlite3
from pathlib import Path
from typing import Optional

from antigravity_suite.proto.wire import read_varint


def _extract_meta_timestamp(meta: bytes) -> Optional[str]:
    """Scans protobuf metadata bytes for authentic unix epoch timestamps."""
    pos = 0
    while pos < len(meta):
        tw, pos = read_varint(meta, pos)
        w, _ = tw & 7, tw >> 3
        if w == 0:
            v, pos = read_varint(meta, pos)
            if 1000000000 < v < 2000000000:
                dt = datetime.datetime.fromtimestamp(v, tz=datetime.timezone.utc)
                return dt.strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
        elif w == 2:
            l, pos = read_varint(meta, pos)
            sub = meta[pos : pos + l]
            pos += l
            p2 = 0
            while p2 < len(sub):
                tw2, p2 = read_varint(sub, p2)
                w2, _ = tw2 & 7, tw2 >> 3
                if w2 == 0:
                    v2, p2 = read_varint(sub, p2)
                    if 1000000000 < v2 < 2000000000:
                        dt = datetime.datetime.fromtimestamp(v2, tz=datetime.timezone.utc)
                        return dt.strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
                elif w2 == 2:
                    l2, p2 = read_varint(sub, p2)
                    p2 += l2
                elif w2 in (1, 5):
                    p2 += 8 if w2 == 1 else 4
                else:
                    break
        elif w in (1, 5):
            pos += 8 if w == 1 else 4
        else:
            break
    return None


def get_step_db_timestamp(db_file: Path) -> Optional[str]:
    """Reads authentic step timestamp from conversation database steps table."""
    if not db_file.is_file() or db_file.stat().st_size == 0:
        return None
    conn = None
    try:
        conn = sqlite3.connect(str(db_file), timeout=5.0)
        cur = conn.cursor()
        cur.execute("SELECT metadata FROM steps ORDER BY idx DESC LIMIT 10;")
        for (meta,) in cur.fetchall():
            if not meta:
                continue
            ts = _extract_meta_timestamp(meta)
            if ts:
                return ts
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return None


def get_fallback_authentic_timestamp(db_file: Path, brain_dir: Path) -> Optional[str]:
    """Extracts fallback authentic timestamp from steps table or brain directory mtime."""
    step_ts = get_step_db_timestamp(db_file)
    if step_ts:
        return step_ts
    if brain_dir.is_dir():
        try:
            mtime = brain_dir.stat().st_mtime
            dt = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)
            ts = dt.strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
            if "2026-10-20 22:5" not in ts:
                return ts
        except Exception:
            pass
    return None
