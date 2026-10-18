"""
Protobuf Encoder for VS Code antigravityUnifiedStateSync State.
"""

from __future__ import annotations

import base64
from typing import Dict, Optional

from antigravity_suite.proto.wire import (
    encode_tag_bytes,
    extract_pure_binary_summary,
    read_varint,
)


def build_unified_state_sync(all_summaries: Dict[str, bytes], existing_raw_b64: Optional[str] = None) -> str:
    """Constructs base64-encoded Protobuf payload for `antigravityUnifiedStateSync`."""
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

    traj_topic_entry = bytearray()
    traj_topic_entry += encode_tag_bytes(1, b"trajectorySummaries")
    traj_topic_entry += encode_tag_bytes(2, bytes(topic_bytes))

    other_topics = _extract_other_topics(existing_raw_b64)

    out = bytearray()
    out += encode_tag_bytes(1, bytes(traj_topic_entry))
    out += other_topics
    return base64.b64encode(bytes(out)).decode("ascii")


def _extract_other_topics(existing_raw_b64: Optional[str]) -> bytearray:
    other_topics = bytearray()
    if not existing_raw_b64:
        return other_topics
    try:
        old_data = base64.b64decode(existing_raw_b64)
        pos, total = 0, len(old_data)
        while pos < total:
            start_field = pos
            tag_wire, pos = read_varint(old_data, pos)
            wire_type, tag_num = tag_wire & 7, tag_wire >> 3
            if wire_type == 0:
                _, pos = read_varint(old_data, pos)
            elif wire_type == 1:
                pos += 8
            elif wire_type == 2:
                length, pos = read_varint(old_data, pos)
                field_val = old_data[pos : pos + length]
                pos += length
                if tag_num == 1:
                    sub_pos, sub_key = 0, ""
                    while sub_pos < len(field_val):
                        st_wire, sub_pos = read_varint(field_val, sub_pos)
                        st_wire_type, st_num = st_wire & 7, st_wire >> 3
                        if st_wire_type == 2:
                            slen, sub_pos = read_varint(field_val, sub_pos)
                            if st_num == 1:
                                sub_key = field_val[sub_pos : sub_pos + slen].decode("ascii", "ignore")
                            sub_pos += slen
                        elif st_wire_type == 0:
                            _, sub_pos = read_varint(field_val, sub_pos)
                    if sub_key != "trajectorySummaries":
                        other_topics += old_data[start_field:pos]
            elif wire_type == 5:
                pos += 4
            else:
                break
    except Exception:
        pass
    return other_topics
