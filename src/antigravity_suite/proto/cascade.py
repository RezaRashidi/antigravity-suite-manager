"""
Protobuf Serializer and Parser for Antigravity Cascade Trajectory Summaries.

Encodes and decodes the native binary summary format used in
conversation_summaries.db and state.vscdb:
  Tag 1:  summary / initial user prompt (string)
  Tag 2:  step_count (varint)
  Tag 3:  last_modified_time (google.protobuf.Timestamp)
  Tag 4:  trajectory_id (string UUID)
  Tag 5:  last_modified_time (legacy compatibility)
  Tag 6:  status (varint: 1 = IDLE)
  Tag 7:  trajectory_type (varint: 4)
  Tag 8:  source (varint: 1 = CASCADE_SOURCE_USER)
  Tag 9:  project_id (string)
  Tag 10: agent_name (string: 'antigravity-agent')
  Tag 14: last_user_input_time (google.protobuf.Timestamp)
  Tag 15: title submessage (Tag 1 = title string, Tag 7 = timestamp)
  Tag 16: last_user_input_step_index (varint)
  Tag 19: workspace_uris (repeated string)
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

UUID_REGEX = re.compile(r"^[0-9a-fA-F-]{36}$")


def get_last_user_step_index(db_path: Path, fallback_step_count: int = 0) -> int:
    """Reads the highest index where step_type = 14 (User prompt) from conversation database."""
    if not db_path.is_file():
        return max(0, fallback_step_count - 1)
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=15.0)
        row = conn.cursor().execute("SELECT MAX(idx) FROM steps WHERE step_type = 14;").fetchone()
        if row and row[0] is not None:
            return int(row[0])
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return max(0, fallback_step_count - 1)


def build_cascade_summary(
    uuid: str,
    title: str,
    summary: str,
    step_count: int,
    last_modified_iso: Optional[str] = None,
    last_user_step: int = -1,
    workspace_uri: Optional[Union[str, List[str]]] = None,
    project_id: Optional[str] = None,
) -> bytes:
    """
    Serializes conversation metadata into authentic Antigravity CascadeTrajectorySummary binary protobuf.
    """
    if not last_modified_iso:
        last_modified_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
    if last_user_step < 0 and step_count > 0:
        last_user_step = max(0, step_count - 1)

    ts_bytes = encode_timestamp_field(last_modified_iso)
    effective_title = title or summary or "Conversation"
    effective_summary = summary or title or "Conversation"

    out = bytearray()

    # Tag 1: summary / prompt text
    out += encode_tag_bytes(1, effective_summary.encode("utf-8"))

    # Tag 2: step_count
    out += encode_tag_uint(2, max(1, step_count))

    # Tag 3: last_modified_time timestamp
    out += encode_tag_bytes(3, ts_bytes)

    # Tag 4: trajectory_id (UUID)
    out += encode_tag_bytes(4, uuid.encode("utf-8"))

    # Tag 5: last_modified_time (compatibility)
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

    # Tag 15: title submessage (Tag 1 = title, Tag 7 = timestamp)
    sub_15 = bytearray()
    sub_15 += encode_tag_bytes(1, effective_title.encode("utf-8"))
    sub_15 += encode_tag_bytes(7, ts_bytes)
    out += encode_tag_bytes(15, bytes(sub_15))

    # Tag 16: annotations submessage (Subtag 4 = last_user_step, Subtag 5 = step_count)
    ann_bytes = encode_annotations_field(max(1, step_count), max(0, last_user_step))
    out += encode_tag_bytes(16, ann_bytes)

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
    supporting both native Google Antigravity tag layout and legacy formats.
    """
    res: Dict[Any, Any] = {}
    if not data:
        return res

    pos = 0
    data_len = len(data)
    tag_strings: Dict[int, str] = {}

    while pos < data_len:
        tag_wire, pos = read_varint(data, pos)
        wire_type = tag_wire & 7
        tag_num = tag_wire >> 3

        if wire_type == 0:  # Varint
            val, pos = read_varint(data, pos)
            res[tag_num] = val
            if tag_num == 2:
                res["step_count"] = val
            elif tag_num == 16:
                res["last_user_step"] = val
        elif wire_type == 2:  # Length-delimited
            length, pos = read_varint(data, pos)
            val_bytes = data[pos : pos + length]
            pos += length
            res[tag_num] = val_bytes

            # Attempt UTF-8 decoding for string candidate tags
            if tag_num in (1, 3, 4, 9, 10, 19):
                try:
                    decoded_str = val_bytes.decode("utf-8")
                    tag_strings[tag_num] = decoded_str
                except Exception:
                    pass

            if tag_num == 9 and tag_num in tag_strings:
                res["project_id"] = tag_strings[9]
            elif tag_num == 19 and tag_num in tag_strings:
                w_uri = tag_strings[19]
                res.setdefault("workspace_uris", []).append(w_uri)
                if "workspace_uri" not in res:
                    res["workspace_uri"] = w_uri
            elif tag_num == 15:
                # Submessage containing title
                try:
                    p15 = 0
                    while p15 < len(val_bytes):
                        tw15, p15 = read_varint(val_bytes, p15)
                        w15 = tw15 & 7
                        t15 = tw15 >> 3
                        if w15 == 2:
                            l15, p15 = read_varint(val_bytes, p15)
                            b15 = val_bytes[p15 : p15 + l15]
                            p15 += l15
                            if t15 == 1:
                                res["title"] = b15.decode("utf-8")
                        elif w15 == 0:
                            _, p15 = read_varint(val_bytes, p15)
                        elif w15 == 1:
                            p15 += 8
                        elif w15 == 5:
                            p15 += 4
                except Exception:
                    pass
            elif tag_num == 16:
                # Legacy submessage annotations
                try:
                    p16 = 0
                    while p16 < len(val_bytes):
                        tw16, p16 = read_varint(val_bytes, p16)
                        w16 = tw16 & 7
                        t16 = tw16 >> 3
                        if w16 == 0:
                            v16, p16 = read_varint(val_bytes, p16)
                            if t16 == 4:
                                res["last_user_step"] = v16
                        elif w16 == 2:
                            l16, p16 = read_varint(val_bytes, p16)
                            p16 += l16
                except Exception:
                    pass
            elif tag_num in (3, 5, 14):
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

    # Resolve UUID / Trajectory ID
    if 4 in tag_strings and UUID_REGEX.match(tag_strings[4]):
        res["trajectory_id"] = tag_strings[4]
    elif 1 in tag_strings and UUID_REGEX.match(tag_strings[1]):
        res["trajectory_id"] = tag_strings[1]

    # Resolve Summary
    if 1 in tag_strings and not UUID_REGEX.match(tag_strings[1]):
        res["summary"] = tag_strings[1]
    elif 4 in tag_strings and not UUID_REGEX.match(tag_strings[4]):
        res["summary"] = tag_strings[4]

    # Resolve Title
    if "title" not in res or not res["title"]:
        if 3 in tag_strings and tag_strings[3] and not tag_strings[3].startswith("\x08"):
            res["title"] = tag_strings[3]
        elif "summary" in res and res["summary"]:
            res["title"] = res["summary"]

    return res
