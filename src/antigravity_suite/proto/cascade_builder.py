"""
Cascade Trajectory Summary Protobuf Serializer.
"""

from __future__ import annotations

import datetime
from typing import List, Optional, Union

from antigravity_suite.proto.wire import (
    encode_tag_bytes,
    encode_tag_uint,
    encode_timestamp_field,
)


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
    """Serializes conversation metadata into authentic Antigravity CascadeTrajectorySummary binary."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
    if not last_modified_iso or str(last_modified_iso).startswith("0001"):
        last_modified_iso = now_iso
    if not created_iso or str(created_iso).startswith("0001"):
        created_iso = last_modified_iso
    if not last_user_input_iso or str(last_user_input_iso).startswith("0001"):
        last_user_input_iso = last_modified_iso

    if last_user_step < 0 and step_count > 0:
        last_user_step = max(0, step_count - 1)

    ts_mod = encode_timestamp_field(last_modified_iso)
    ts_created = encode_timestamp_field(created_iso)
    ts_input = encode_timestamp_field(last_user_input_iso)

    out = bytearray()
    out += encode_tag_bytes(1, (summary or title or "Conversation").encode("utf-8"))
    out += encode_tag_uint(2, max(1, step_count))
    out += encode_tag_bytes(3, ts_mod)
    out += encode_tag_bytes(4, uuid.encode("utf-8"))
    out += encode_tag_uint(5, 1)
    out += encode_tag_bytes(7, ts_created)

    ws_list = [workspace_uri] if isinstance(workspace_uri, str) else (workspace_uri or [])
    for w in ws_list:
        if w:
            sw = encode_tag_bytes(1, str(w).encode("utf-8")) + encode_tag_bytes(2, str(w).encode("utf-8"))
            out += encode_tag_bytes(9, sw)

    out += encode_tag_bytes(10, ts_input)
    out += encode_tag_bytes(15, _build_annotations_submessage(title or summary or "Conversation", ts_mod, pinned, archived))
    out += encode_tag_uint(16, max(0, last_user_step))
    out += encode_tag_bytes(17, _build_metadata_submessage(uuid, ws_list, ts_created, project_id))

    if source != 0:
        out += encode_tag_uint(20, source)
    out += encode_tag_uint(22, 4)
    return bytes(out)


def _build_annotations_submessage(title: str, ts_mod: bytes, pinned: bool, archived: bool) -> bytes:
    sub = bytearray()
    sub += encode_tag_bytes(1, title.encode("utf-8"))
    sub += encode_tag_bytes(7, ts_mod)
    if pinned:
        sub += encode_tag_uint(12, 1)
    if archived:
        sub += encode_tag_uint(4, 1)
    return bytes(sub)


def _build_metadata_submessage(uuid: str, ws_list: list, ts_created: bytes, project_id: Optional[str]) -> bytes:
    sub = bytearray()
    if ws_list and ws_list[0]:
        sw = encode_tag_bytes(1, str(ws_list[0]).encode("utf-8")) + encode_tag_bytes(2, str(ws_list[0]).encode("utf-8"))
        sub += encode_tag_bytes(1, sw)
        sub += encode_tag_bytes(7, str(ws_list[0]).encode("utf-8"))
    sub += encode_tag_bytes(2, ts_created)
    sub += encode_tag_bytes(6, uuid.encode("utf-8"))
    if project_id:
        sub += encode_tag_bytes(18, project_id.encode("utf-8"))
        sub += encode_tag_bytes(14, project_id.encode("utf-8"))
    return bytes(sub)
