"""
Protocol Buffers Wire Format, Cascade Summaries, and Metadata Package.
"""

from antigravity_suite.proto.cascade import (
    build_cascade_summary,
    get_last_user_step_index,
    parse_cascade_summary,
)
from antigravity_suite.proto.trajectory import (
    build_trajectory_metadata_blob,
    parse_trajectory_metadata_blob,
)
from antigravity_suite.proto.vscdb import (
    build_sidebar_workspace_bytes,
    build_summaries_state,
    build_unified_state_sync,
    parse_sidebar_workspaces,
    update_sidebar_workspaces_state,
)
from antigravity_suite.proto.wire import (
    encode_annotations_field,
    encode_tag_bytes,
    encode_tag_uint,
    encode_timestamp_field,
    encode_varint,
    extract_entries_from_proto,
    extract_pure_binary_summary,
    read_varint,
)

__all__ = [
    "encode_varint",
    "read_varint",
    "encode_tag_bytes",
    "encode_tag_uint",
    "encode_timestamp_field",
    "encode_annotations_field",
    "extract_pure_binary_summary",
    "extract_entries_from_proto",
    "build_cascade_summary",
    "parse_cascade_summary",
    "get_last_user_step_index",
    "build_trajectory_metadata_blob",
    "parse_trajectory_metadata_blob",
    "build_summaries_state",
    "build_unified_state_sync",
    "build_sidebar_workspace_bytes",
    "parse_sidebar_workspaces",
    "update_sidebar_workspaces_state",
]
