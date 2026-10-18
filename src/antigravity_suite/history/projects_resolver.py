"""
Project ID and Workspace URI Bidirectional Resolvers.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, Optional

from antigravity_suite.config import get_user_home
import antigravity_suite.history.projects_constants as pc
from antigravity_suite.history.projects_mappings import discover_project_mappings
from antigravity_suite.history.projects_normalize import normalize_workspace_uri
from antigravity_suite.history.projects_roots import get_candidate_gemini_dirs


def get_project_id_for_workspace(
    ws_uri: Optional[str],
    user_home: Optional[Path] = None,
    mappings: Optional[Dict[str, str]] = None,
    create_missing: bool = False,
) -> Optional[str]:
    """Resolves canonical project_id for a workspace URI dynamically."""
    if not ws_uri:
        return None
    ws_norm = normalize_workspace_uri(ws_uri, user_home=user_home)
    if not ws_norm:
        return None

    home = user_home or get_user_home()
    if mappings is None:
        mappings = discover_project_mappings(home)

    if ws_norm in mappings:
        return mappings[ws_norm]
    if ws_norm in pc.KNOWN_PROJECT_MAPPINGS:
        return pc.KNOWN_PROJECT_MAPPINGS[ws_norm]

    refreshed = discover_project_mappings(home, force_refresh=True)
    if ws_norm in refreshed:
        mappings[ws_norm] = refreshed[ws_norm]
        return refreshed[ws_norm]

    if not create_missing:
        return None

    det_id = str(uuid.uuid5(uuid.NAMESPACE_URL, ws_norm))
    mappings[ws_norm] = det_id
    pc.KNOWN_PROJECT_MAPPINGS[ws_norm] = det_id
    if pc._PROJECT_MAPPINGS_CACHE is not None:
        pc._PROJECT_MAPPINGS_CACHE[ws_norm] = det_id
    return det_id


def get_workspace_for_project_id(
    project_id: Optional[str],
    user_home: Optional[Path] = None,
) -> Optional[str]:
    """Resolves canonical workspace URI for a given project UUID."""
    if not project_id or str(project_id).strip() in ("outside-of-project", "default-cli-project"):
        return None

    home = user_home or get_user_home()
    clean_pid = str(project_id).strip()

    for gdir in get_candidate_gemini_dirs(home):
        p_file = gdir / "config" / "projects" / f"{clean_pid}.json"
        if p_file.is_file():
            try:
                with open(p_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for r in data.get("projectResources", {}).get("resources", []):
                    furi = r.get("folderUri") or r.get("gitFolder", {}).get("folderUri")
                    if furi and str(furi).startswith("file://"):
                        return str(furi).strip().rstrip("`\"';,")
            except Exception:
                pass

    for ws, pid in pc.KNOWN_PROJECT_MAPPINGS.items():
        if pid == clean_pid and ws.startswith("file://"):
            return ws
    return None
