"""
Low-Level Protocol Buffers (Protobuf) Wire Format Encoders and Decoders.
"""

from __future__ import annotations

from antigravity_suite.proto.wire_extractor import extract_entries_from_proto
from antigravity_suite.proto.wire_fields import (
    encode_annotations_field,
    encode_timestamp_field,
)
from antigravity_suite.proto.wire_pure import (
    extract_pure_binary_summary,
    is_plausible_proto as _is_plausible_proto,
)
from antigravity_suite.proto.wire_varint import (
    encode_tag_bytes,
    encode_tag_uint,
    encode_varint,
    read_varint,
)

__all__ = [
    "encode_varint",
    "read_varint",
    "encode_tag_bytes",
    "encode_tag_uint",
    "encode_timestamp_field",
    "encode_annotations_field",
    "_is_plausible_proto",
    "extract_pure_binary_summary",
    "extract_entries_from_proto",
]
