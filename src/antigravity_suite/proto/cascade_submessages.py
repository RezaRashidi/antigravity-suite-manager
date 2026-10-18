"""
Cascade Trajectory Protobuf Submessage Parsers.
"""

from __future__ import annotations

import datetime
import struct
from typing import Any, Dict

from antigravity_suite.proto.wire import read_varint


def parse_workspaces_field(val_bytes: bytes, res: Dict[Any, Any]) -> None:
    try:
        p9 = 0
        while p9 < len(val_bytes):
            tw9, p9 = read_varint(val_bytes, p9)
            w9, t9 = tw9 & 7, tw9 >> 3
            if w9 == 2:
                l9, p9 = read_varint(val_bytes, p9)
                b9 = val_bytes[p9 : p9 + l9]
                p9 += l9
                if t9 == 1:
                    uri_str = b9.decode("utf-8", "ignore")
                    res.setdefault("workspace_uris", []).append(uri_str)
                    res.setdefault("workspace_uri", uri_str)
            elif w9 == 0:
                _, p9 = read_varint(val_bytes, p9)
            elif w9 in (1, 5):
                p9 += 8 if w9 == 1 else 4
            else:
                break
    except Exception:
        pass
    if "workspace_uri" not in res:
        try:
            res["project_id"] = val_bytes.decode("utf-8")
        except Exception:
            pass


def parse_annotations_field(val_bytes: bytes, res: Dict[Any, Any]) -> None:
    try:
        p15 = 0
        while p15 < len(val_bytes):
            tw15, p15 = read_varint(val_bytes, p15)
            w15, t15 = tw15 & 7, tw15 >> 3
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
            elif w15 in (1, 5):
                p15 += 8 if w15 == 1 else 4
            else:
                break
    except Exception:
        pass


def parse_timestamp_field(val_bytes: bytes, tag_num: int, res: Dict[Any, Any]) -> None:
    try:
        p_ts, s_secs = 0, None
        while p_ts < len(val_bytes):
            tw_ts, p_ts = read_varint(val_bytes, p_ts)
            w_ts, t_ts = tw_ts & 7, tw_ts >> 3
            if w_ts == 0:
                v_ts, p_ts = read_varint(val_bytes, p_ts)
                if t_ts == 1:
                    s_secs = struct.unpack("<q", struct.pack("<Q", v_ts & 0xFFFFFFFFFFFFFFFF))[0]
            elif w_ts == 2:
                l_ts, p_ts = read_varint(val_bytes, p_ts)
                p_ts += l_ts
            elif w_ts in (1, 5):
                p_ts += 8 if w_ts == 1 else 4
            else:
                break
        if s_secs is not None and s_secs >= 1000000000:
            dt = datetime.datetime.fromtimestamp(s_secs, tz=datetime.timezone.utc)
            iso_str = dt.strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
            res[f"ts_{tag_num}"] = iso_str
            tag_map = {3: "last_modified_iso", 7: "created_iso", 10: "last_user_input_iso", 14: "last_user_input_iso"}
            if tag_num in tag_map:
                res.setdefault(tag_map[tag_num], iso_str)
        elif tag_num in (3, 7, 10):
            res["has_bad_timestamp"] = True
    except Exception:
        if tag_num in (3, 7, 10):
            res["has_bad_timestamp"] = True
