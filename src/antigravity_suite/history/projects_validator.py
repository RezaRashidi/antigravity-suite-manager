"""
Workspace URI and Container Root Validation Helpers.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit

from antigravity_suite.config import get_user_home
from antigravity_suite.history.projects_constants import PROJECT_CONTAINERS


@lru_cache(maxsize=2048)
def is_container_or_system_root(uri_str: str, user_home: Optional[Path] = None) -> bool:
    """Returns True if uri_str is a parent container folder or system root."""
    if not uri_str:
        return True
    path_str = unquote(urlsplit(uri_str).path).replace("\\", "/").rstrip("/")
    if path_str in ("/tmp", "/var/tmp", "/home", "/Users", "") or path_str.count("/") <= 2:
        return True

    home_str = str((user_home or get_user_home()).resolve()).replace("\\", "/").rstrip("/")
    if path_str == home_str:
        return True
    if path_str.startswith(home_str + "/"):
        rel = path_str[len(home_str) + 1 :]
        if "/" not in rel and rel.lower() in PROJECT_CONTAINERS:
            return True

    parts = path_str.split("/")
    if len(parts) == 4 and parts[1].lower() in ("home", "users") and parts[3].lower() in PROJECT_CONTAINERS:
        return True
    if len(parts) >= 2 and parts[-1].lower() in PROJECT_CONTAINERS and not (Path(path_str) / ".git").exists():
        return True
    return False


@lru_cache(maxsize=2048)
def is_valid_workspace_uri(uri: Optional[str], user_home: Optional[Path] = None) -> bool:
    """Validates if workspace URI is well-formed and points to an authentic directory."""
    if not uri or not isinstance(uri, str):
        return False
    u = uri.strip().rstrip("`\"';,")
    if not u.startswith("file://") or any(c in u for c in ("\n", "\r", "`", "<", ">", '"', "'")):
        return False
    if any(k in u for k in ("outside-of-project", ".gemini/antigravity/brain", ".config/Antigravity")):
        return False

    path_str = unquote(urlsplit(u).path)
    if not path_str or path_str in ("/", "\\"):
        return False

    home = (user_home or get_user_home()).resolve()
    if is_container_or_system_root(u, user_home=home):
        return False

    p = Path(path_str)
    try:
        if str(home) in path_str:
            return p.is_dir()
        if p.exists():
            return p.is_dir()
    except Exception:
        pass
    return True
