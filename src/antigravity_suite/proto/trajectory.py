"""
Trajectory Metadata Protobuf Builder and Parser.
"""

from __future__ import annotations

from antigravity_suite.proto.trajectory_builder import build_trajectory_metadata_blob
from antigravity_suite.proto.trajectory_parser import parse_trajectory_metadata_blob

__all__ = [
    "build_trajectory_metadata_blob",
    "parse_trajectory_metadata_blob",
]
