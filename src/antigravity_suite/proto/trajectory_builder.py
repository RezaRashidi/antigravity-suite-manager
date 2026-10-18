"""
Trajectory Metadata Protobuf Builder.
"""

from __future__ import annotations

from typing import Optional

from antigravity_suite.config import DEFAULT_CONFIG
from antigravity_suite.proto.wire import encode_tag_bytes


def build_trajectory_metadata_blob(
    conv_id: str,
    workspace_uri: Optional[str] = None,
    project_id: Optional[str] = None,
) -> bytes:
    """Builds a valid Protobuf binary trajectory_metadata_blob."""
    effective_uri = workspace_uri or DEFAULT_CONFIG.default_workspace_uri
    effective_project = project_id or DEFAULT_CONFIG.default_project_id

    out = bytearray()
    ws = bytearray()
    ws += encode_tag_bytes(1, effective_uri.encode("utf-8"))
    ws += encode_tag_bytes(2, effective_uri.encode("utf-8"))

    out += encode_tag_bytes(1, bytes(ws))
    out += encode_tag_bytes(6, conv_id.encode("utf-8"))
    out += encode_tag_bytes(7, effective_uri.encode("utf-8"))
    out += encode_tag_bytes(18, effective_project.encode("utf-8"))

    return bytes(out)
