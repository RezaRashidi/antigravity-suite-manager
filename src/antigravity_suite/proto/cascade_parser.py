"""
Protobuf Parser for Antigravity Cascade Trajectory Summaries.
"""

from __future__ import annotations

from typing import Any, Dict

from antigravity_suite.proto.cascade_metadata import (
    parse_legacy_annotations,
    parse_metadata_submessage,
    resolve_cascade_identity,
)
from antigravity_suite.proto.cascade_submessages import (
    parse_annotations_field,
    parse_timestamp_field,
    parse_workspaces_field,
)
from antigravity_suite.proto.wire import read_varint

_CASCADE_CACHE: Dict[bytes, Dict[Any, Any]] = {}


def clear_cascade_cache() -> None:
    """Clears the cascade summary cache."""
    _CASCADE_CACHE.clear()


def parse_cascade_summary(data: bytes) -> Dict[Any, Any]:
    """Parses a Protobuf binary CascadeTrajectorySummary into a dictionary."""
    if not data:
        return {}
    cached = _CASCADE_CACHE.get(data)
    if cached is not None:
        return cached.copy()

    res: Dict[Any, Any] = {}
    if b"\x80\x92\xb8\xc3\x98\xfe\xff\xff\xff\x01" in data:
        res["has_bad_timestamp"] = True

    pos, data_len = 0, len(data)
    tag_strings: Dict[int, str] = {}

    while pos < data_len:
        tag_wire, pos = read_varint(data, pos)
        wire_type, tag_num = tag_wire & 7, tag_wire >> 3

        if wire_type == 0:
            val, pos = read_varint(data, pos)
            res[tag_num] = val
            field_map = {2: "step_count", 5: "status", 16: "last_user_step", 20: "source", 22: "trajectory_type"}
            if tag_num in field_map:
                res[field_map[tag_num]] = val
        elif wire_type == 2:
            length, pos = read_varint(data, pos)
            val_bytes = data[pos : pos + length]
            pos += length
            res[tag_num] = val_bytes

            if tag_num in (1, 4, 19):
                try:
                    tag_strings[tag_num] = val_bytes.decode("utf-8")
                except Exception:
                    pass

            if tag_num == 19 and 19 in tag_strings:
                res.setdefault("workspace_uris", []).append(tag_strings[19])
                res.setdefault("workspace_uri", tag_strings[19])
            elif tag_num == 9:
                parse_workspaces_field(val_bytes, res)
            elif tag_num == 15:
                parse_annotations_field(val_bytes, res)
            elif tag_num == 16:
                parse_legacy_annotations(val_bytes, res)
            elif tag_num == 17:
                parse_metadata_submessage(val_bytes, res)
            elif tag_num in (3, 5, 7, 10, 14):
                parse_timestamp_field(val_bytes, tag_num, res)
        elif wire_type in (1, 5):
            pos += 8 if wire_type == 1 else 4
        else:
            break

    resolve_cascade_identity(tag_strings, res)
    if len(_CASCADE_CACHE) > 5000:
        _CASCADE_CACHE.clear()
    _CASCADE_CACHE[data] = res
    return res.copy()
