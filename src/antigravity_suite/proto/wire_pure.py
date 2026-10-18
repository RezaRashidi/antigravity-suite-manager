"""
Extraction and Unwrapping of Pure Binary Protobuf Summaries.
"""

from __future__ import annotations

import base64
import re
from typing import Any, Optional

from antigravity_suite.proto.wire_varint import read_varint


def is_plausible_proto(b: bytes) -> bool:
    if not b or len(b) < 4:
        return False
    wire_type = b[0] & 7
    tag_num = b[0] >> 3
    return wire_type in (0, 2) and 1 <= tag_num <= 30


def extract_pure_binary_summary(raw: Any) -> Optional[bytes]:
    """Extracts raw protobuf binary summary unwrapping Base64 or Value wrappers."""
    if not raw or not isinstance(raw, (bytes, bytearray)):
        return None
    raw_bytes = bytes(raw)

    if len(raw_bytes) >= 8 and re.match(rb"^[A-Za-z0-9+/=\s]+$", raw_bytes):
        try:
            decoded = base64.b64decode(raw_bytes)
            if is_plausible_proto(decoded):
                return extract_pure_binary_summary(decoded)
        except Exception:
            pass

    if len(raw_bytes) >= 4 and raw_bytes[0] in (0x0A, 0x1A):
        length, pos = read_varint(raw_bytes, 1)
        if pos + length == len(raw_bytes) and length >= 4:
            cand = raw_bytes[pos : pos + length]
            if re.match(rb"^[A-Za-z0-9+/=\s]+$", cand):
                try:
                    decoded = base64.b64decode(cand)
                    if is_plausible_proto(decoded):
                        return extract_pure_binary_summary(decoded)
                except Exception:
                    pass

    return raw_bytes
