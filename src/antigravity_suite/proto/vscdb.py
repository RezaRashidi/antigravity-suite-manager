"""
Protobuf Helpers for VS Code state.vscdb Global Storage.

Encodes conversation summaries and unified state sync into Base64-wrapped
Protocol Buffer payloads expected by Antigravity IDE (VS Code edition).
"""

from __future__ import annotations

import base64
from typing import Dict, Optional

from antigravity_suite.proto.wire import (
    encode_tag_bytes,
    extract_pure_binary_summary,
    read_varint,
)


def build_summaries_state(all_summaries: Dict[str, bytes]) -> str:
    """
    Constructs the base64-encoded Protobuf payload for `antigravityUnifiedStateSync.trajectorySummaries`:
      Root: repeated entry Tag 1
        Submessage:
          Tag 1: uuid (string)
          Tag 2: cascade_summary (pure_bin bytes)
    """
    entries = bytearray()
    for uuid, pure_bin in sorted(all_summaries.items()):
        raw = extract_pure_binary_summary(pure_bin)
        if raw and len(raw) >= 10:
            entry = bytearray()
            entry += encode_tag_bytes(1, uuid.encode("utf-8"))
            entry += encode_tag_bytes(2, raw)
            entries += encode_tag_bytes(1, bytes(entry))

    b64_str = base64.b64encode(bytes(entries)).decode("ascii")
    # Wrap in google.protobuf.Value string format (Tag 3 = string_value)
    val_wrap = bytearray()
    val_wrap += encode_tag_bytes(3, b64_str.encode("utf-8"))
    return base64.b64encode(bytes(val_wrap)).decode("ascii")


def build_unified_state_sync(all_summaries: Dict[str, bytes], existing_raw_b64: Optional[str] = None) -> str:
    """
    Constructs the base64-encoded Protobuf payload for `antigravityUnifiedStateSync`:
      Tag 1: submessage containing repeated Tag 1 (uuid, pure_bin)
    Preserves other tags (!= 1) from existing_raw_b64 if present.
    """
    entries = bytearray()
    for uuid, pure_bin in sorted(all_summaries.items()):
        raw = extract_pure_binary_summary(pure_bin)
        if raw and len(raw) >= 10:
            entry = bytearray()
            entry += encode_tag_bytes(1, uuid.encode("utf-8"))
            entry += encode_tag_bytes(2, raw)
            entries += encode_tag_bytes(1, bytes(entry))

    other_fields = bytearray()
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
                    pos += length
                elif wire_type == 5:
                    pos += 4
                else:
                    break
                if tag_num != 1 and pos <= total:
                    other_fields.extend(old_data[start_field:pos])
        except Exception:
            pass

    outer = bytearray()
    outer += encode_tag_bytes(1, bytes(entries))
    outer += other_fields
    return base64.b64encode(bytes(outer)).decode("ascii")
