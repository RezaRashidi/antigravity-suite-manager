"""
Project Mapping Constants and In-Memory Registries.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

PROJECT_CONTAINERS: Set[str] = {
    "phpstormprojects", "webstormprojects", "pycharmprojects", "ideaprojects",
    "vscodeprojects", "projects", "project", "workspace", "workspaces", "repos",
    "repo", "dev", "code", "development", "desktop", "downloads", "documents",
    "music", "videos", "pictures", "library",
}

KNOWN_ROOTS: List[str] = []
KNOWN_PROJECT_MAPPINGS: Dict[str, str] = {}
_PROJECT_MAPPINGS_CACHE: Optional[Dict[str, str]] = None
_LAST_MAPPINGS_DISCOVERY_TIME: float = 0.0


def register_known_root(root_uri: str) -> None:
    """Registers a root workspace URI into the active KNOWN_ROOTS cache."""
    if root_uri and root_uri not in KNOWN_ROOTS:
        KNOWN_ROOTS.append(root_uri)
        try:
            from antigravity_suite.history.projects_normalize import normalize_workspace_uri
            normalize_workspace_uri.cache_clear()
        except Exception:
            pass


def register_project_mapping(workspace_uri: str, project_id: str) -> None:
    """Registers a workspace-to-project-id mapping in the active runtime cache."""
    if workspace_uri and project_id:
        KNOWN_PROJECT_MAPPINGS[workspace_uri] = project_id


def clear_workspace_caches() -> None:
    """Clears workspace normalization and project mapping runtime caches."""
    import antigravity_suite.history.projects_constants as pc
    pc._PROJECT_MAPPINGS_CACHE = None
    pc._LAST_MAPPINGS_DISCOVERY_TIME = 0.0
    try:
        from antigravity_suite.history.projects_validator import is_container_or_system_root, is_valid_workspace_uri
        from antigravity_suite.history.projects_normalize import normalize_workspace_uri
        is_container_or_system_root.cache_clear()
        is_valid_workspace_uri.cache_clear()
        normalize_workspace_uri.cache_clear()
    except Exception:
        pass
