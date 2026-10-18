"""
Protobuf Serializer and Parser for Antigravity Cascade Trajectory Summaries.
"""

from __future__ import annotations

from antigravity_suite.proto.cascade_builder import build_cascade_summary
from antigravity_suite.proto.cascade_parser import parse_cascade_summary
from antigravity_suite.proto.cascade_step import get_last_user_step_index
from antigravity_suite.proto.wire_varint import encode_tag_bytes, encode_tag_uint

__all__ = [
    "get_last_user_step_index",
    "build_cascade_summary",
    "parse_cascade_summary",
    "encode_tag_bytes",
    "encode_tag_uint",
]
