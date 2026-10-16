"""
Protobuf Helpers for VS Code state.vscdb Global Storage.

Encodes conversation summaries, unified state sync, and sidebar workspaces
into Base64-wrapped Protocol Buffer payloads expected by Antigravity IDE (VS Code edition).
"""

from __future__ import annotations

import base64
from typing import Dict, List, Optional

from antigravity_suite.proto.wire import (
    encode_tag_bytes,
    encode_tag_uint,
    extract_pure_binary_summary,
    read_varint,
)


def build_summaries_state(all_summaries: Dict[str, bytes]) -> str:
    """
    Constructs the base64-encoded Protobuf payload for `antigravityUnifiedStateSync.trajectorySummaries`:
      Root: Topic (message)
        Tag 1: repeated DataEntry data = 1
          Tag 1: key (string = conversation_uuid)
          Tag 2: value (Row message)
            Tag 1: value (string = base64-encoded cascade_summary bytes)
            Tag 2: e_tag (int64) [optional, e.g. timestamp or 0]
    """
    entries = bytearray()
    for uuid, pure_bin in sorted(all_summaries.items()):
        raw = extract_pure_binary_summary(pure_bin)
        if raw and len(raw) >= 10:
            cascade_b64 = base64.b64encode(raw).decode("ascii")
            row = bytearray()
            row += encode_tag_bytes(1, cascade_b64.encode("utf-8"))

            entry = bytearray()
            entry += encode_tag_bytes(1, uuid.encode("utf-8"))
            entry += encode_tag_bytes(2, bytes(row))
            entries += encode_tag_bytes(1, bytes(entry))

    return base64.b64encode(bytes(entries)).decode("ascii")


def build_unified_state_sync(all_summaries: Dict[str, bytes], existing_raw_b64: Optional[str] = None) -> str:
    """
    Constructs the base64-encoded Protobuf payload for `antigravityUnifiedStateSync`:
      Root: UssState (message)
        Tag 1: map<string, Topic> topics = 1
          repeated TopicsEntry topics = 1
            Tag 1: key (string = "trajectorySummaries")
            Tag 2: value (Topic message bytes)
    Preserves other topics (!= "trajectorySummaries") from existing_raw_b64 if present.
    """
    topic_bytes = bytearray()
    for uuid, pure_bin in sorted(all_summaries.items()):
        raw = extract_pure_binary_summary(pure_bin)
        if raw and len(raw) >= 10:
            cascade_b64 = base64.b64encode(raw).decode("ascii")
            row = bytearray()
            row += encode_tag_bytes(1, cascade_b64.encode("utf-8"))

            entry = bytearray()
            entry += encode_tag_bytes(1, uuid.encode("utf-8"))
            entry += encode_tag_bytes(2, bytes(row))
            topic_bytes += encode_tag_bytes(1, bytes(entry))

    # Construct TopicsEntry for trajectorySummaries
    traj_topic_entry = bytearray()
    traj_topic_entry += encode_tag_bytes(1, b"trajectorySummaries")
    traj_topic_entry += encode_tag_bytes(2, bytes(topic_bytes))

    other_topics = bytearray()
    if existing_raw_b64:
        try:
            old_data = base64.b64decode(existing_raw_b64)
            pos = 0
            total = len(old_data)
            while pos < total:
                start_field = pos
                tag_wire, pos = read_varint(old_data, pos)
                wire_type = tag_wire & 7
                tag_num = tag_wire >> 3
                if wire_type == 0:
                    _, pos = read_varint(old_data, pos)
                elif wire_type == 1:
                    pos += 8
                elif wire_type == 2:
                    length, pos = read_varint(old_data, pos)
                    field_val = old_data[pos : pos + length]
                    pos += length
                    if tag_num == 1:
                        # Inspect TopicsEntry key
                        sub_pos = 0
                        sub_key = ""
                        while sub_pos < len(field_val):
                            st_wire, sub_pos = read_varint(field_val, sub_pos)
                            st_num = st_wire >> 3
                            st_type = st_wire & 7
                            if st_type == 2:
                                s_len, sub_pos = read_varint(field_val, sub_pos)
                                if st_num == 1:
                                    sub_key = field_val[sub_pos : sub_pos + s_len].decode("utf-8", "ignore")
                                sub_pos += s_len
                            elif st_type == 0:
                                _, sub_pos = read_varint(field_val, sub_pos)
                            else:
                                break
                        if sub_key == "trajectorySummaries":
                            continue
                elif wire_type == 5:
                    pos += 4
                else:
                    break
                if pos <= total:
                    other_topics.extend(old_data[start_field:pos])
        except Exception:
            pass

    outer = bytearray()
    outer += encode_tag_bytes(1, bytes(traj_topic_entry))
    outer += other_topics
    return base64.b64encode(bytes(outer)).decode("ascii")


def build_sidebar_workspace_bytes(ws_uri: str, order: int = -1) -> bytes:
    """
    Constructs a SidebarWorkspace protobuf binary payload for a workspace URI:
      Tag 4: uri (string)
      Tag 5: display_state (WorkspaceSectionDisplayState submessage)
        Tag 2: only_show_first_few_convos = true (1)
        Tag 3: sidebar_order (int64 -1 or specified)
    """
    disp = bytearray()
    disp += encode_tag_uint(2, 1)  # only_show_first_few_convos = True
    disp += encode_tag_uint(3, order if order >= 0 else 0xFFFFFFFFFFFFFFFF)
    sw = bytearray()
    sw += encode_tag_bytes(4, ws_uri.encode("utf-8"))
    sw += encode_tag_bytes(5, bytes(disp))
    return bytes(sw)


def parse_sidebar_workspaces(val_b64: Optional[str]) -> Dict[str, bytes]:
    """Parses existing sidebarWorkspaces Topic from base64 string."""
    workspaces: Dict[str, bytes] = {}
    if not val_b64:
        return workspaces
    try:
        raw = base64.b64decode(val_b64)
    except Exception:
        return workspaces
    pos = 0
    total = len(raw)
    while pos < total:
        try:
            tw, pos = read_varint(raw, pos)
            l, pos = read_varint(raw, pos)
            entry_raw = raw[pos : pos + l]
            pos += l
            epos = 0
            k = None
            v = None
            while epos < len(entry_raw):
                etw, epos = read_varint(entry_raw, epos)
                etag = etw >> 3
                el, epos = read_varint(entry_raw, epos)
                eval_ = entry_raw[epos : epos + el]
                epos += el
                if etag == 1:
                    k = eval_.decode("utf-8", "ignore")
                elif etag == 2:
                    v = eval_
            if k:
                workspaces[k] = v or b""
        except Exception:
            break
    return workspaces


def update_sidebar_workspaces_state(existing_b64: Optional[str], active_workspaces: List[str]) -> str:
    """
    Ensures all active workspace URIs are present in the sidebarWorkspaces Topic.
    Preserves existing settings and orders while appending new workspaces.
    """
    ws_dict = parse_sidebar_workspaces(existing_b64)
    for w in active_workspaces:
        if w and w not in ws_dict:
            inner = build_sidebar_workspace_bytes(w)
            inner_b64 = base64.b64encode(inner).decode("ascii")
            row = bytearray()
            row += encode_tag_bytes(1, inner_b64.encode("utf-8"))
            ws_dict[w] = bytes(row)

    entries = bytearray()
    for k, v in sorted(ws_dict.items()):
        entry = bytearray()
        entry += encode_tag_bytes(1, k.encode("utf-8"))
        entry += encode_tag_bytes(2, v)
        entries += encode_tag_bytes(1, bytes(entry))
    return base64.b64encode(bytes(entries)).decode("ascii")
