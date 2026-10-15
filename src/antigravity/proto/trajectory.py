"""
Trajectory Metadata Protobuf Builder and Parser.

Populates the trajectory_metadata_blob (table in conversation SQLite databases)
which binds conversations to project workspaces, git roots, and project IDs in Antigravity IDE.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from antigravity.config import DEFAULT_CONFIG
from antigravity.proto.wire import encode_tag_bytes, read_varint


def build_trajectory_metadata_blob(
    conv_id: str,
    workspace_uri: Optional[str] = None,
    project_id: Optional[str] = None,
) -> bytes:
    """
    Builds a valid Protobuf binary trajectory_metadata_blob matching native Antigravity databases:
      Tag 1:  workspaces (submessage: Tag 1 = workspaceFolderAbsoluteUri, Tag 2 = gitRootAbsoluteUri)
      Tag 6:  rootConversationId (string)
      Tag 7:  workspaceUris (repeated string)
      Tag 18: projectId (string)
    """
    effective_uri = workspace_uri or DEFAULT_CONFIG.default_workspace_uri
    effective_project = project_id or DEFAULT_CONFIG.default_project_id

    out = bytearray()
    ws = bytearray()
    ws += encode_tag_bytes(1, effective_uri.encode("utf-8"))
    ws += encode_tag_bytes(2, effective_uri.encode("utf-8"))

    out += encode_tag_bytes(1, bytes(ws))
    out += encode_tag_bytes(6, conv_id.encode("utf-8"))
    out += encode_tag_bytes(7, effective_uri.encode("utf-8"))
    out += encode_tag_bytes(18, effective_project.encode("utf-8"))

    return bytes(out)


def parse_trajectory_metadata_blob(data: bytes) -> Dict[str, Any]:
    """Parses a trajectory_metadata_blob into a dictionary of workspace/project fields."""
    res: Dict[str, Any] = {}
    pos = 0
    data_len = len(data)

    while pos < data_len:
        tag_wire, pos = read_varint(data, pos)
        wire_type = tag_wire & 7
        tag_num = tag_wire >> 3

        if wire_type == 2:
            length, pos = read_varint(data, pos)
            val_bytes = data[pos : pos + length]
            pos += length

            if tag_num == 1:
                # workspaces submessage
                p_sub = 0
                while p_sub < len(val_bytes):
                    sub_tw, p_sub = read_varint(val_bytes, p_sub)
                    sub_wire = sub_tw & 7
                    sub_tag = sub_tw >> 3
                    if sub_wire == 2:
                        sub_len, p_sub = read_varint(val_bytes, p_sub)
                        sub_data = val_bytes[p_sub : p_sub + sub_len]
                        p_sub += sub_len
                        if sub_tag == 1:
                            res["workspace_folder"] = sub_data.decode("utf-8", errors="ignore")
                        elif sub_tag == 2:
                            res["git_root"] = sub_data.decode("utf-8", errors="ignore")
                    elif sub_wire == 0:
                        _, p_sub = read_varint(val_bytes, p_sub)
                    else:
                        break
            elif tag_num == 6:
                res["root_conversation_id"] = val_bytes.decode("utf-8", errors="ignore")
            elif tag_num == 7:
                res["workspace_uri"] = val_bytes.decode("utf-8", errors="ignore")
            elif tag_num == 18:
                res["project_id"] = val_bytes.decode("utf-8", errors="ignore")
        elif wire_type == 0:
            _, pos = read_varint(data, pos)
        else:
            break

    return res
