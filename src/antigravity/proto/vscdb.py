"""
Protobuf Helpers for VS Code state.vscdb Global Storage.

Encodes conversation summaries and unified state sync into Base64-wrapped
Protocol Buffer payloads expected by Antigravity IDE (VS Code edition).
"""

from __future__ import annotations

import base64
from typing import Dict

from antigravity.proto.wire import (
    encode_tag_bytes,
    encode_tag_uint,
    extract_pure_binary_summary,
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


def build_unified_state_sync(all_summaries: Dict[str, bytes]) -> str:
    """
    Constructs the base64-encoded Protobuf payload for `antigravityUnifiedStateSync`:
      Tag 1: submessage containing repeated Tag 1 (uuid, pure_bin)
    """
    entries = bytearray()
    for uuid, pure_bin in sorted(all_summaries.items()):
        raw = extract_pure_binary_summary(pure_bin)
        if raw and len(raw) >= 10:
            entry = bytearray()
            entry += encode_tag_bytes(1, uuid.encode("utf-8"))
            entry += encode_tag_bytes(2, raw)
            entries += encode_tag_bytes(1, bytes(entry))

    outer = bytearray()
    outer += encode_tag_bytes(1, bytes(entries))
    return base64.b64encode(bytes(outer)).decode("ascii")
