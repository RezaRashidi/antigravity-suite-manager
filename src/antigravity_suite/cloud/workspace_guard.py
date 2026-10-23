"""
Workspace directory inspection, path translation, and automatic provisioning.
"""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from antigravity_suite.cloud.constants import REAL_HOME
from antigravity_suite.history.vscdb_meta import get_db_trajectory_meta


def resolve_local_workspace_path(uri: str, real_home: str = REAL_HOME) -> str | None:
    """Translates a workspace URI into an absolute filesystem path on the local system."""
    if not uri or not uri.startswith("file://"):
        return None
    raw_path = unquote(urlsplit(uri).path)
    if not raw_path:
        return None

    path_obj = Path(raw_path)
    if path_obj.is_dir():
        return str(path_obj)

    # Cross-user path translation: if /home/user1/projects/x, map to /home/current/projects/x
    m = re.match(r"^/(home|Users)/([^/]+)/(.*)$", raw_path)
    if m:
        sub_rel = m.group(3)
        candidate = os.path.join(real_home, sub_rel)
        return candidate

    return raw_path


def ensure_workspace_exists(workspace_path: str) -> bool:
    """Creates the workspace directory if it does not already exist."""
    if not workspace_path or workspace_path in ["/", "/home", "/tmp"]:
        return False
    if os.path.isdir(workspace_path):
        return False  # Already exists

    try:
        os.makedirs(workspace_path, exist_ok=True)
        marker = os.path.join(workspace_path, ".antigravity_synced_workspace")
        if not os.path.exists(marker):
            with open(marker, "w") as f:
                f.write("# Automatically provisioned by Antigravity Cloud Sync\n")
        return True
    except Exception:
        return False


def provision_workspaces_for_dbs(conv_dir: str, real_home: str = REAL_HOME) -> list[str]:
    """Scans conversation databases and auto-creates any missing workspace directories."""
    created = []
    if not os.path.isdir(conv_dir):
        return created

    for db_path in glob.glob(os.path.join(conv_dir, "*.db")):
        uri, _ = get_db_trajectory_meta(db_path)
        if uri:
            local_p = resolve_local_workspace_path(uri, real_home=real_home)
            if local_p and ensure_workspace_exists(local_p):
                created.append(local_p)
    return created
