"""
CascadeTrajectorySummary Protobuf Builder and Parser.

Constructs and parses the binary representation of conversation summaries
used by Antigravity Hub, Electron UI sidebars, and conversation_summaries.db.
"""

from __future__ import annotations

import datetime
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from antigravity_suite.proto.wire import (
    encode_annotations_field,
    encode_tag_bytes,
    encode_tag_uint,
    encode_timestamp_field,
    read_varint,
)


def get_last_user_step_index(db_path: Union[str, Path], step_count: int = 0) -> int:
    """
    Finds the last user prompt step index (`step_type = 14`) in the SQLite database.
    Setting this field in CascadeTrajectorySummary prevents spurious 'New' badges.
    """
    if os.path.isfile(db_path):
        conn = None
        try:
            conn = sqlite3.connect(db_path, timeout=15.0)
            cur = conn.cursor()
            cur.execute("SELECT idx FROM steps WHERE step_type = 14 ORDER BY idx DESC LIMIT 1;")
            row = cur.fetchone()
            if row is not None and row[0] is not None:
                return int(row[0])
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    return max(0, step_count - 1) if step_count > 0 else 0


def build_cascade_summary(
    uuid: str,
    title: str,
    summary: str,
    step_count: int = 1,
    last_modified_iso: Optional[str] = None,
    last_user_step: int = -1,
    workspace_uri: Optional[Union[str, List[str]]] = None,
    project_id: Optional[str] = None,
) -> bytes:
    """
    Builds a valid Protobuf binary CascadeTrajectorySummary matching the official schema:
      Tag 1:  trajectory_id (string)
      Tag 2:  step_count (uint64)
      Tag 3:  title (string)
      Tag 4:  summary (string)
      Tag 5:  last_modified_time (google.protobuf.Timestamp)
      Tag 6:  status (varint: 1 = IDLE)
      Tag 7:  trajectory_type (varint: 4)
      Tag 8:  source (varint: 1 = CASCADE_SOURCE_USER)
      Tag 9:  project_id (string)
      Tag 10: agent_name (string: 'antigravity-agent')
      Tag 14: last_user_input_time (google.protobuf.Timestamp)
      Tag 16: annotations / read state (submessage: Tag 4 = last_user_step, Tag 5 = step_count)
      Tag 19: workspace_uris (repeated string)
    """
    if not last_modified_iso:
        last_modified_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
    if last_user_step < 0 and step_count > 0:
        last_user_step = max(0, step_count - 1)

    out = bytearray()
    # Tag 1: trajectory_id
    out += encode_tag_bytes(1, uuid.encode("utf-8"))
    # Tag 2: step_count
    out += encode_tag_uint(2, max(1, step_count))
    # Tag 3: title
    out += encode_tag_bytes(3, title.encode("utf-8"))
    # Tag 4: summary
    out += encode_tag_bytes(4, summary.encode("utf-8"))
    # Tag 5: last_modified_time
    ts_bytes = encode_timestamp_field(last_modified_iso)
    out += encode_tag_bytes(5, ts_bytes)
    # Tag 6: status (1 = IDLE)
    out += encode_tag_uint(6, 1)
    # Tag 7: trajectory_type (4)
    out += encode_tag_uint(7, 4)
    # Tag 8: source (1)
    out += encode_tag_uint(8, 1)
    # Tag 9: project_id
    p_id = project_id or "outside-of-project"
    out += encode_tag_bytes(9, p_id.encode("utf-8"))
    # Tag 10: agent_name
    out += encode_tag_bytes(10, b"antigravity-agent")
    # Tag 14: last_user_input_time
    out += encode_tag_bytes(14, ts_bytes)
    # Tag 16: annotations
    anno_bytes = encode_annotations_field(step_count, last_user_step)
    out += encode_tag_bytes(16, anno_bytes)
    # Tag 19: workspace_uris
    if isinstance(workspace_uri, list):
        for w in workspace_uri:
            if w:
                out += encode_tag_bytes(19, str(w).encode("utf-8"))
    elif workspace_uri:
        out += encode_tag_bytes(19, str(workspace_uri).encode("utf-8"))

    return bytes(out)


def parse_cascade_summary(data: bytes) -> Dict[Any, Any]:
    """
    Parses a Protobuf binary CascadeTrajectorySummary into a dictionary
    containing named keys ('title', 'summary', 'trajectory_id') and numeric tag IDs.
    """
    res: Dict[Any, Any] = {}
    pos = 0
    data_len = len(data)

    while pos < data_len:
        tag_wire, pos = read_varint(data, pos)
        wire_type = tag_wire & 7
        tag_num = tag_wire >> 3

        if wire_type == 0:  # Varint
            val, pos = read_varint(data, pos)
            res[tag_num] = val
            if tag_num == 2:
                res["step_count"] = val
        elif wire_type == 2:  # Length-delimited
            length, pos = read_varint(data, pos)
            val_bytes = data[pos : pos + length]
            pos += length
            res[tag_num] = val_bytes

            # Map known string fields
            if tag_num == 1:
                try:
                    res["trajectory_id"] = val_bytes.decode("utf-8")
                except Exception:
                    pass
            elif tag_num == 3:
                try:
                    res["title"] = val_bytes.decode("utf-8")
                except Exception:
                    pass
            elif tag_num == 4:
                try:
                    res["summary"] = val_bytes.decode("utf-8")
                except Exception:
                    pass
            elif tag_num == 9:
                try:
                    res["project_id"] = val_bytes.decode("utf-8")
                except Exception:
                    pass
            elif tag_num == 19:
                try:
                    w_uri = val_bytes.decode("utf-8")
                    res.setdefault("workspace_uris", []).append(w_uri)
                    if "workspace_uri" not in res:
                        res["workspace_uri"] = w_uri
                except Exception:
                    pass
            elif tag_num in (5, 14):
                # Timestamp submessage
                try:
                    p_ts = 0
                    tw_ts, p_ts = read_varint(val_bytes, p_ts)
                    if (tw_ts >> 3) == 1 and (tw_ts & 7) == 0:
                        secs, _ = read_varint(val_bytes, p_ts)
                        dt = datetime.datetime.fromtimestamp(secs, tz=datetime.timezone.utc)
                        res[f"ts_{tag_num}"] = dt.strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
                except Exception:
                    pass
        elif wire_type == 1:
            pos += 8
        elif wire_type == 5:
            pos += 4
        else:
            break

    return res
