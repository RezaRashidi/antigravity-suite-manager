"""
Workspace URI Normalization Engine.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit

from antigravity_suite.config import get_user_home
from antigravity_suite.history.projects_constants import (
    KNOWN_ROOTS,
    PROJECT_CONTAINERS,
    register_known_root,
)
from antigravity_suite.history.projects_roots import discover_workspace_roots
from antigravity_suite.history.projects_validator import is_container_or_system_root


@lru_cache(maxsize=1024)
def normalize_workspace_uri(
    uri: Optional[str],
    user_home: Optional[Path] = None,
) -> Optional[str]:
    """Normalizes subfolder workspace paths to their respective root workspace URIs."""
    if not uri:
        return None
    uri_str = str(uri).strip()
    if uri_str.startswith("["):
        try:
            arr = json.loads(uri_str)
            if arr:
                uri_str = str(arr[0]).strip()
        except Exception:
            pass
    uri_str = uri_str.rstrip("`\"';,")
    if not uri_str.startswith("file://"):
        return uri_str

    roots = sorted(list(KNOWN_ROOTS) or discover_workspace_roots(user_home), key=len, reverse=True)
    for root in roots:
        if uri_str == root:
            return root
        if not is_container_or_system_root(root) and (uri_str.startswith(root + "/") or uri_str.startswith(root + "\\")):
            return root

    path_str = unquote(urlsplit(uri_str).path)
    if path_str:
        p = Path(path_str)
        home_path = (user_home or get_user_home()).resolve()
        if p.exists() or p.parent.exists():
            curr = p if p.is_dir() else p.parent
            while curr and curr != curr.parent:
                if curr.resolve() == home_path or str(curr) in ("/", "\\"):
                    break
                if (curr / ".git").exists():
                    root_uri = f"file://{curr.resolve()}"
                    register_known_root(root_uri)
                    return root_uri
                curr = curr.parent

        clean_path = path_str.replace("\\", "/")
        home_str = str(home_path).replace("\\", "/").rstrip("/")
        if clean_path.startswith(home_str + "/"):
            rel = clean_path[len(home_str) + 1 :]
            rel_parts = rel.split("/")
            if len(rel_parts) >= 2 and rel_parts[0].lower() in PROJECT_CONTAINERS:
                root_uri = f"file://{home_str}/{rel_parts[0]}/{rel_parts[1]}"
                register_known_root(root_uri)
                return root_uri

        parts = clean_path.split("/")
        start_idx = 3 if len(parts) >= 3 and parts[1].lower() in ("home", "users") else 0
        for i in range(start_idx, len(parts) - 1):
            if parts[i].lower() in PROJECT_CONTAINERS:
                root_uri = f"file://{'/'.join(parts[: i + 2])}"
                register_known_root(root_uri)
                return root_uri

    return uri_str
