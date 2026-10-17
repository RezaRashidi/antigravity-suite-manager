"""
Protobuf Serializer and Parser for Antigravity Cascade Trajectory Summaries.

Encodes and decodes the native binary summary format used in
conversation_summaries.db, agyhub_summaries_proto.pb, and state.vscdb:
  Tag 1:  summary / initial user prompt (string)
  Tag 2:  step_count (uint32 varint)
  Tag 3:  last_modified_time (google.protobuf.Timestamp)
  Tag 4:  trajectory_id (string UUID)
  Tag 5:  status (varint: 1 = CASCADE_RUN_STATUS_IDLE)
  Tag 7:  created_time (google.protobuf.Timestamp)
  Tag 9:  workspaces (repeated CortexWorkspaceMetadata: Tag 1 = uri, Tag 2 = git_root)
  Tag 10: last_user_input_time (google.protobuf.Timestamp)
  Tag 15: annotations submessage (Tag 1 = title string, Tag 7 = view timestamp)
  Tag 16: last_user_input_step_index (uint32 varint)
  Tag 17: trajectory_metadata (CortexTrajectoryMetadata)
  Tag 20: source (varint: 1 = CASCADE_SOURCE_USER)
  Tag 22: trajectory_type (varint: 4)
"""

from __future__ import annotations

import datetime
import os
import re
import sqlite3
import struct
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
    last_modified_iso: Optional[Union[str, datetime.datetime, int, float]] = None,
    last_user_step: int = -1,
    workspace_uri: Optional[Union[str, List[str]]] = None,
    project_id: Optional[str] = None,
    created_iso: Optional[Union[str, datetime.datetime, int, float]] = None,
    last_user_input_iso: Optional[Union[str, datetime.datetime, int, float]] = None,
    pinned: bool = False,
    archived: bool = False,
    source: int = 0,
) -> bytes:
    """
    Serializes conversation metadata into authentic Antigravity CascadeTrajectorySummary binary protobuf.
    """
    if not last_modified_iso:
        last_modified_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
    if not created_iso:
        created_iso = last_modified_iso
    if not last_user_input_iso:
        last_user_input_iso = last_modified_iso

    if last_user_step < 0 and step_count > 0:
        last_user_step = max(0, step_count - 1)

    ts_modified = encode_timestamp_field(last_modified_iso)
    ts_created = encode_timestamp_field(created_iso)
    ts_user_input = encode_timestamp_field(last_user_input_iso)

    effective_title = title or summary or "Conversation"
    effective_summary = summary or title or "Conversation"

    out = bytearray()

    # Tag 1: summary / prompt text
    out += encode_tag_bytes(1, effective_summary.encode("utf-8"))

    # Tag 2: step_count
    out += encode_tag_uint(2, max(1, step_count))

    # Tag 3: last_modified_time timestamp
    out += encode_tag_bytes(3, ts_modified)

    # Tag 4: trajectory_id (UUID)
    out += encode_tag_bytes(4, uuid.encode("utf-8"))

    # Tag 5: status (1 = IDLE)
    out += encode_tag_uint(5, 1)

    # Tag 7: created_time timestamp
    out += encode_tag_bytes(7, ts_created)

    # Tag 9: workspaces (CortexWorkspaceMetadata)
    ws_list = [workspace_uri] if isinstance(workspace_uri, str) else (workspace_uri or [])
    for w in ws_list:
        if w:
            sub_ws = bytearray()
            sub_ws += encode_tag_bytes(1, str(w).encode("utf-8"))
            sub_ws += encode_tag_bytes(2, str(w).encode("utf-8"))
            out += encode_tag_bytes(9, bytes(sub_ws))

    # Tag 10: last_user_input_time (google.protobuf.Timestamp)
    out += encode_tag_bytes(10, ts_user_input)

    # Tag 15: annotations submessage (Tag 1 = title, Tag 4 = archived, Tag 7 = view timestamp, Tag 8 = marked_as_unread, Tag 12 = pinned)
    sub_15 = bytearray()
    sub_15 += encode_tag_bytes(1, effective_title.encode("utf-8"))
    sub_15 += encode_tag_bytes(7, ts_modified)
    if pinned:
        sub_15 += encode_tag_uint(12, 1)
    if archived:
        sub_15 += encode_tag_uint(4, 1)
    out += encode_tag_bytes(15, bytes(sub_15))

    # Tag 16: last_user_input_step_index (uint32 varint)
    out += encode_tag_uint(16, max(0, last_user_step))

    # Tag 17: trajectory_metadata (CortexTrajectoryMetadata)
    sub_17 = bytearray()
    if ws_list and ws_list[0]:
        sub_ws_17 = bytearray()
        sub_ws_17 += encode_tag_bytes(1, str(ws_list[0]).encode("utf-8"))
        sub_ws_17 += encode_tag_bytes(2, str(ws_list[0]).encode("utf-8"))
        sub_17 += encode_tag_bytes(1, bytes(sub_ws_17))
        sub_17 += encode_tag_bytes(7, str(ws_list[0]).encode("utf-8"))
    sub_17 += encode_tag_bytes(2, ts_created)
    sub_17 += encode_tag_bytes(6, uuid.encode("utf-8"))
    if project_id:
        sub_17 += encode_tag_bytes(18, project_id.encode("utf-8"))
        sub_17 += encode_tag_bytes(14, project_id.encode("utf-8"))
    out += encode_tag_bytes(17, bytes(sub_17))

    # Tag 20: source (CortexTrajectorySource: 0 = UNSPECIFIED / local, 18 = JETBOX)
    # Native Antigravity omits tag 20 for local conversations so mna(source) is True.
    # Emitting tag 20 as 1 (CASCADE_CLIENT) causes Antigravity UI to classify it as external
    # and drop it from the sidebar conversation list!
    if source != 0:
        out += encode_tag_uint(20, source)

    # Tag 22: trajectory_type (4)
    out += encode_tag_uint(22, 4)

    return bytes(out)


def parse_cascade_summary(data: bytes) -> Dict[Any, Any]:
    """
    Parses a Protobuf binary CascadeTrajectorySummary into a dictionary
    supporting both native Google Antigravity tag layout and legacy formats.
    Detects corrupt or Year 1 (0001-01-01) timestamps.
    """
    res: Dict[Any, Any] = {}
    if not data:
        return res

    if b"\x80\x92\xb8\xc3\x98\xfe\xff\xff\xff\x01" in data:
        res["has_bad_timestamp"] = True

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
            elif tag_num == 5:
                res["status"] = val
            elif tag_num == 16:
                res["last_user_step"] = val
            elif tag_num == 20:
                res["source"] = val
            elif tag_num == 22:
                res["trajectory_type"] = val
        elif wire_type == 2:  # Length-delimited
            length, pos = read_varint(data, pos)
            val_bytes = data[pos : pos + length]
            pos += length
            res[tag_num] = val_bytes

            # Attempt UTF-8 decoding for string candidate tags
            if tag_num in (1, 4, 19):
                try:
                    decoded_str = val_bytes.decode("utf-8")
                    tag_strings[tag_num] = decoded_str
                except Exception:
                    pass

            if tag_num == 19 and tag_num in tag_strings:
                w_uri = tag_strings[19]
                res.setdefault("workspace_uris", []).append(w_uri)
                if "workspace_uri" not in res:
                    res["workspace_uri"] = w_uri
            elif tag_num == 9:
                # Can be CortexWorkspaceMetadata submessage or legacy string
                try:
                    p9 = 0
                    while p9 < len(val_bytes):
                        tw9, p9 = read_varint(val_bytes, p9)
                        w9 = tw9 & 7
                        t9 = tw9 >> 3
                        if w9 == 2:
                            l9, p9 = read_varint(val_bytes, p9)
                            b9 = val_bytes[p9 : p9 + l9]
                            p9 += l9
                            if t9 == 1:
                                uri_str = b9.decode("utf-8", "ignore")
                                res.setdefault("workspace_uris", []).append(uri_str)
                                if "workspace_uri" not in res:
                                    res["workspace_uri"] = uri_str
                        elif w9 == 0:
                            _, p9 = read_varint(val_bytes, p9)
                        elif w9 == 1:
                            p9 += 8
                        elif w9 == 5:
                            p9 += 4
                        else:
                            break
                except Exception:
                    pass
                if "workspace_uri" not in res:
                    try:
                        str9 = val_bytes.decode("utf-8")
                        res["project_id"] = str9
                    except Exception:
                        pass
            elif tag_num == 15:
                # Submessage containing title and last_user_view_time
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
                                res["title"] = b15.decode("utf-8", "ignore")
                        elif w15 == 0:
                            v15, p15 = read_varint(val_bytes, p15)
                            if t15 == 12:
                                res["pinned"] = bool(v15)
                            elif t15 in (4, 8):
                                res["archived"] = bool(v15)
                        elif w15 == 1:
                            p15 += 8
                        elif w15 == 5:
                            p15 += 4
                        else:
                            break
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
                        else:
                            break
                except Exception:
                    pass
            elif tag_num == 17:
                # CortexTrajectoryMetadata submessage
                try:
                    p17 = 0
                    while p17 < len(val_bytes):
                        tw17, p17 = read_varint(val_bytes, p17)
                        w17 = tw17 & 7
                        t17 = tw17 >> 3
                        if w17 == 2:
                            l17, p17 = read_varint(val_bytes, p17)
                            b17 = val_bytes[p17 : p17 + l17]
                            p17 += l17
                            if t17 == 18:
                                res["project_id"] = b17.decode("utf-8", "ignore")
                                res["has_tag_18"] = True
                            elif t17 == 14:
                                if "project_id" not in res:
                                    res["project_id"] = b17.decode("utf-8", "ignore")
                                res["has_tag_14"] = True
                            elif t17 == 6:
                                res["root_conversation_id"] = b17.decode("utf-8", "ignore")
                            elif t17 == 7:
                                uri_str = b17.decode("utf-8", "ignore")
                                if "workspace_uri" not in res:
                                    res["workspace_uri"] = uri_str
                            elif t17 == 1:
                                try:
                                    p_sub = 0
                                    while p_sub < len(b17):
                                        tw_sub, p_sub = read_varint(b17, p_sub)
                                        w_sub = tw_sub & 7
                                        t_sub = tw_sub >> 3
                                        if w_sub == 2:
                                            l_sub, p_sub = read_varint(b17, p_sub)
                                            sub_val = b17[p_sub : p_sub + l_sub]
                                            p_sub += l_sub
                                            if t_sub == 1 and "workspace_uri" not in res:
                                                res["workspace_uri"] = sub_val.decode("utf-8", "ignore")
                                        elif w_sub == 0:
                                            _, p_sub = read_varint(b17, p_sub)
                                        elif w_sub == 1:
                                            p_sub += 8
                                        elif w_sub == 5:
                                            p_sub += 4
                                        else:
                                            break
                                except Exception:
                                    pass
                        elif w17 == 0:
                            _, p17 = read_varint(val_bytes, p17)
                        elif w17 == 1:
                            p17 += 8
                        elif w17 == 5:
                            p17 += 4
                        else:
                            break
                except Exception:
                    pass
            elif tag_num in (3, 5, 7, 10, 14):
                # Timestamp submessage
                try:
                    p_ts = 0
                    s_secs = None
                    while p_ts < len(val_bytes):
                        tw_ts, p_ts = read_varint(val_bytes, p_ts)
                        w_ts = tw_ts & 7
                        t_ts = tw_ts >> 3
                        if w_ts == 0:
                            v_ts, p_ts = read_varint(val_bytes, p_ts)
                            if t_ts == 1:
                                s_secs = struct.unpack("<q", struct.pack("<Q", v_ts & 0xFFFFFFFFFFFFFFFF))[0]
                        elif w_ts == 2:
                            l_ts, p_ts = read_varint(val_bytes, p_ts)
                            p_ts += l_ts
                        elif w_ts == 1:
                            p_ts += 8
                        elif w_ts == 5:
                            p_ts += 4
                        else:
                            break
                    if s_secs is not None:
                        if s_secs < 1000000000:
                            res["has_bad_timestamp"] = True
                        else:
                            dt = datetime.datetime.fromtimestamp(s_secs, tz=datetime.timezone.utc)
                            iso_str = dt.strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
                            res[f"ts_{tag_num}"] = iso_str
                            if tag_num == 3:
                                res["last_modified_iso"] = iso_str
                            elif tag_num == 7:
                                res["created_iso"] = iso_str
                            elif tag_num == 10:
                                res["last_user_input_iso"] = iso_str
                            elif tag_num == 14:
                                res.setdefault("last_user_input_iso", iso_str)
                    else:
                        if tag_num in (3, 7, 10):
                            res["has_bad_timestamp"] = True
                except Exception:
                    if tag_num in (3, 7, 10):
                        res["has_bad_timestamp"] = True
        elif wire_type == 1:
            pos += 8
        elif wire_type == 5:
            pos += 4
        else:
            break

    # Resolve UUID / Trajectory ID
    if 4 in tag_strings and UUID_REGEX.match(tag_strings[4]):
        res["trajectory_id"] = tag_strings[4]
    elif "root_conversation_id" in res and UUID_REGEX.match(res["root_conversation_id"]):
        res["trajectory_id"] = res["root_conversation_id"]
    elif 1 in tag_strings and UUID_REGEX.match(tag_strings[1]):
        res["trajectory_id"] = tag_strings[1]

    # Resolve Summary
    if 1 in tag_strings and not UUID_REGEX.match(tag_strings[1]):
        res["summary"] = tag_strings[1]
    elif 4 in tag_strings and not UUID_REGEX.match(tag_strings[4]):
        res["summary"] = tag_strings[4]

    # Resolve Title
    if "title" not in res or not res["title"]:
        if "summary" in res and res["summary"]:
            res["title"] = res["summary"]

    return res
