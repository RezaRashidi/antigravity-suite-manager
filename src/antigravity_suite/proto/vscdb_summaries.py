"""
Protobuf Encoder for VS Code trajectorySummaries State.
"""

from __future__ import annotations

import base64
from typing import Dict

from antigravity_suite.proto.wire import (
    encode_tag_bytes,
    extract_pure_binary_summary,
)


def build_summaries_state(all_summaries: Dict[str, bytes]) -> str:
    """Constructs base64-encoded Protobuf payload for `antigravityUnifiedStateSync.trajectorySummaries`."""
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
