"""
Workspace URI Validation and Self-Healing Resolver.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from antigravity_suite.history.projects import (
    get_workspace_for_project_id,
    is_valid_workspace_uri,
)
from antigravity_suite.history.synthesizer import extract_workspace_from_transcript


def heal_workspace_uri(
    ws_uri: str,
    meta: Dict[str, Any],
    parsed_raw: Dict[str, Any],
    existing_proj: Optional[str] = None,
) -> str:
    """Validates workspace URI; heals poisoned or non-existent URIs via project mappings/transcripts."""
    if is_valid_workspace_uri(ws_uri):
        return ws_uri

    effective_pid = existing_proj or meta.get("db_proj_id") or parsed_raw.get("project_id")
    healed_ws = None
    if effective_pid:
        healed_ws = get_workspace_for_project_id(effective_pid)
    if not healed_ws and meta.get("transcript_file"):
        healed_ws = extract_workspace_from_transcript(meta["transcript_file"], project_id=effective_pid)

    if healed_ws and is_valid_workspace_uri(healed_ws):
        return healed_ws
    return ""
