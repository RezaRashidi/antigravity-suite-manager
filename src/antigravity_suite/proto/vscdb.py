"""
Protobuf Helpers for VS Code state.vscdb Global Storage.
"""

from __future__ import annotations

from antigravity_suite.proto.vscdb_summaries import build_summaries_state
from antigravity_suite.proto.vscdb_unified import build_unified_state_sync
from antigravity_suite.proto.vscdb_workspaces import (
    build_sidebar_workspace_bytes,
    parse_sidebar_workspaces,
    update_sidebar_workspaces_state,
)

__all__ = [
    "build_summaries_state",
    "build_unified_state_sync",
    "build_sidebar_workspace_bytes",
    "parse_sidebar_workspaces",
    "update_sidebar_workspaces_state",
]
