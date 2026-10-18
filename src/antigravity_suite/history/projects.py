"""
Project Mapping and Configuration Manager Facade.
"""

from __future__ import annotations

from antigravity_suite.history.projects_config_gen import (
    ensure_project_configs,
)
from antigravity_suite.history.projects_constants import (
    KNOWN_PROJECT_MAPPINGS,
    KNOWN_ROOTS,
    PROJECT_CONTAINERS,
    clear_workspace_caches,
    register_known_root,
    register_project_mapping,
)
from antigravity_suite.history.projects_mappings import (
    discover_project_mappings,
)
from antigravity_suite.history.projects_normalize import (
    normalize_workspace_uri,
)
from antigravity_suite.history.projects_resolver import (
    get_project_id_for_workspace,
    get_workspace_for_project_id,
)
from antigravity_suite.history.projects_roots import (
    discover_workspace_roots,
    get_candidate_gemini_dirs,
)
from antigravity_suite.history.projects_validator import (
    is_container_or_system_root,
    is_valid_workspace_uri,
)

__all__ = [
    "PROJECT_CONTAINERS",
    "KNOWN_ROOTS",
    "KNOWN_PROJECT_MAPPINGS",
    "register_known_root",
    "register_project_mapping",
    "clear_workspace_caches",
    "is_container_or_system_root",
    "is_valid_workspace_uri",
    "get_candidate_gemini_dirs",
    "discover_workspace_roots",
    "normalize_workspace_uri",
    "discover_project_mappings",
    "ensure_project_configs",
    "get_project_id_for_workspace",
    "get_workspace_for_project_id",
]
