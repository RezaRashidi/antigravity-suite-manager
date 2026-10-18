"""
Trajectory Metadata Protobuf Parser.
"""

from __future__ import annotations

from typing import Any, Dict

from antigravity_suite.proto.wire import read_varint


def parse_trajectory_metadata_blob(data: bytes) -> Dict[str, Any]:
    """Parses a trajectory_metadata_blob into a dictionary of workspace/project fields."""
    res: Dict[str, Any] = {}
    if not data:
        return res
    pos, data_len = 0, len(data)

    while pos < data_len:
        tag_wire, pos = read_varint(data, pos)
        wire_type, tag_num = tag_wire & 7, tag_wire >> 3

        if wire_type == 2:
            length, pos = read_varint(data, pos)
            val_bytes = data[pos : pos + length]
            pos += length

            if tag_num == 1:
                _parse_workspaces_submessage(val_bytes, res)
            elif tag_num == 6:
                res["root_conversation_id"] = val_bytes.decode("utf-8", errors="ignore")
            elif tag_num == 7:
                uri_val = val_bytes.decode("utf-8", errors="ignore")
                res.setdefault("workspace_uris", []).append(uri_val)
                if "workspace_uri" not in res:
                    res["workspace_uri"] = uri_val
            elif tag_num == 18:
                res["project_id"] = val_bytes.decode("utf-8", errors="ignore")
        elif wire_type == 0:
            _, pos = read_varint(data, pos)
        elif wire_type == 1:
            pos += 8
        elif wire_type == 5:
            pos += 4
        else:
            break

    return res


def _parse_workspaces_submessage(val_bytes: bytes, res: Dict[str, Any]) -> None:
    p_sub = 0
    ws_entry: Dict[str, str] = {}
    while p_sub < len(val_bytes):
        sub_tw, p_sub = read_varint(val_bytes, p_sub)
        sub_wire, sub_tag = sub_tw & 7, sub_tw >> 3
        if sub_wire == 2:
            sub_len, p_sub = read_varint(val_bytes, p_sub)
            sub_data = val_bytes[p_sub : p_sub + sub_len]
            p_sub += sub_len
            val = sub_data.decode("utf-8", errors="ignore")
            if sub_tag == 1:
                ws_entry["workspace_folder"] = val
                res.setdefault("workspace_folder", val)
            elif sub_tag == 2:
                ws_entry["git_root"] = val
                res.setdefault("git_root", val)
        elif sub_wire == 0:
            _, p_sub = read_varint(val_bytes, p_sub)
        elif sub_wire == 1:
            p_sub += 8
        elif sub_wire == 5:
            p_sub += 4
        else:
            break
    if ws_entry:
        res.setdefault("workspaces", []).append(ws_entry)
