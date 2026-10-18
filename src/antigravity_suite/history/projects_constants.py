"""
Project Mapping Constants and In-Memory Registries.
"""

from __future__ import annotations

import os
from pathlib import Path
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


def load_dynamic_containers(user_home: Optional[Path] = None) -> None:
    """Loads additional custom project containers from environment or paths.conf."""
    env_c = os.environ.get("ANTIGRAVITY_PROJECT_CONTAINERS")
    if env_c:
        for item in env_c.split(","):
            if item.strip():
                PROJECT_CONTAINERS.add(item.strip().lower())
    try:
        from antigravity_suite.config import get_user_home
        home = user_home or get_user_home()
        conf = home / ".config" / "antigravity" / "paths.conf"
        if conf.is_file():
            with open(conf, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("PROJECT_CONTAINERS=") or line.startswith("CUSTOM_PROJECT_CONTAINERS="):
                        val = line.split("=", 1)[1].strip().strip('"\'')
                        for item in val.split(","):
                            if item.strip():
                                PROJECT_CONTAINERS.add(item.strip().lower())
    except Exception:
        pass


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


load_dynamic_containers()
