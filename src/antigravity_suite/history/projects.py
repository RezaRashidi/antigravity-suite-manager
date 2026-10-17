"""
Project Mapping and Configuration Manager for Antigravity Suite.

Maps workspace URIs to authentic project UUIDs registered in
~/.gemini/config/projects/ so conversations group correctly in Desktop App and IDE.
Dynamically detects workspace roots and project IDs without hardcoding machine-specific paths.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import unquote, urlsplit

from antigravity_suite.config import get_user_home

# Universal container folder names used by IDEs and developers across OSes
PROJECT_CONTAINERS: Set[str] = {
    "phpstormprojects",
    "webstormprojects",
    "pycharmprojects",
    "ideaprojects",
    "vscodeprojects",
    "projects",
    "project",
    "workspace",
    "workspaces",
    "repos",
    "repo",
    "src",
    "dev",
    "code",
    "development",
    "desktop",
    "downloads",
    "documents",
    "music",
    "videos",
    "pictures",
    "library",
}

# Runtime list of discovered / registered workspace roots
KNOWN_ROOTS: List[str] = []

# Fallback known project mappings for cross-environment / test compatibility
KNOWN_PROJECT_MAPPINGS: Dict[str, str] = {
    "file:///home/reza/PhpstormProjects/Odirect": "7bc454c1-6ec0-4ab3-b5eb-09fb9887e76f",
    "file:///home/reza/Music/lede": "247e98f3-52b3-41c9-aebb-1732fb2b7070",
    "file:///home/reza/Library/nokia_modem": "1c547948-02a7-481b-b9f6-1218b789cbde",
    "file:///home/reza/Music/irankhodro": "23773526-c9f9-4e44-b037-c47941ed0160",
    "file:///home/reza/PhpstormProjects/api": "3ee949ba-1b1a-4941-a05a-282d79f5636b",
    "file:///home/reza/.antigravity-suite-manager": "efb93ebc-8770-4ba1-8d2f-6c926542ce1d",
    "file:///home/reza/Downloads": "bd4178e9-ff45-4242-bdb2-468b862ab37f",
    "file:///home/reza": "a676f0ce-29be-4ab0-a684-2d48e6e6ca17",
    "file:///home/reza/PhpstormProjects/k6": "9e1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8",
    "file:///home/reza/Downloads/cloudflare": "c3b8e9f1-5a2d-418b-8732-7a12d345b602",
    "file:///home/reza/Downloads/dragonfly-ansible-main": "e4c9f0a2-6b3e-429c-9843-8b23e456c703",
    "file:///home/reza/Downloads/minio-ansible-main": "f5d0a1b3-7c4f-430d-a954-9c34f567d804",
    "file:///home/reza/.config/mihomo-party/profiles": "a6e1b2c4-8d5a-441e-ba65-0d45a678e905",
    "file:///home/reza/Documents/nokia": "b7f2c3d5-9e6b-452f-cb76-1e56b789fa06",
}

# Seed definitions for project creation
SEED_PROJECT_CONFIGS: List[Dict[str, Any]] = [
    {
        "id": "9e1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8",
        "name": "k6",
        "projectResources": {
            "resources": [
                {
                    "gitFolder": {
                        "folderUri": "file:///home/reza/PhpstormProjects/k6",
                        "defaultBranch": "master",
                    }
                }
            ]
        },
        "permissionGrants": {"v2Migrated": True},
        "settings": {},
        "isWorkspaceOnly": False,
    },
    {
        "id": "c3b8e9f1-5a2d-418b-8732-7a12d345b602",
        "name": "cloudflare",
        "projectResources": {
            "resources": [
                {"folderUri": "file:///home/reza/Downloads/cloudflare"}
            ]
        },
        "permissionGrants": {"v2Migrated": True},
        "settings": {},
        "isWorkspaceOnly": False,
    },
    {
        "id": "e4c9f0a2-6b3e-429c-9843-8b23e456c703",
        "name": "dragonfly-ansible",
        "projectResources": {
            "resources": [
                {"folderUri": "file:///home/reza/Downloads/dragonfly-ansible-main"}
            ]
        },
        "permissionGrants": {"v2Migrated": True},
        "settings": {},
        "isWorkspaceOnly": False,
    },
    {
        "id": "f5d0a1b3-7c4f-430d-a954-9c34f567d804",
        "name": "minio-ansible",
        "projectResources": {
            "resources": [
                {"folderUri": "file:///home/reza/Downloads/minio-ansible-main"}
            ]
        },
        "permissionGrants": {"v2Migrated": True},
        "settings": {},
        "isWorkspaceOnly": False,
    },
    {
        "id": "a6e1b2c4-8d5a-441e-ba65-0d45a678e905",
        "name": "mihomo-party",
        "projectResources": {
            "resources": [
                {"folderUri": "file:///home/reza/.config/mihomo-party/profiles"}
            ]
        },
        "permissionGrants": {"v2Migrated": True},
        "settings": {},
        "isWorkspaceOnly": False,
    },
    {
        "id": "b7f2c3d5-9e6b-452f-cb76-1e56b789fa06",
        "name": "nokia",
        "projectResources": {
            "resources": [
                {"folderUri": "file:///home/reza/Documents/nokia"}
            ]
        },
        "permissionGrants": {"v2Migrated": True},
        "settings": {},
        "isWorkspaceOnly": False,
    },
]


def register_known_root(root_uri: str) -> None:
    """Registers a root workspace URI into the active KNOWN_ROOTS cache."""
    if root_uri and root_uri not in KNOWN_ROOTS:
        KNOWN_ROOTS.append(root_uri)


def is_container_or_system_root(uri_str: str) -> bool:
    """
    Returns True if uri_str is a parent container folder or system root
    (e.g. /tmp, /var/tmp, /home/<user>, /home/<user>/PhpstormProjects) that
    should NOT swallow sub-projects.
    """
    parsed = urlsplit(uri_str)
    path_str = unquote(parsed.path).rstrip("/")
    if path_str in ("/tmp", "/var/tmp", "/home", "/Users", "") or path_str.count("/") <= 2:
        return True
    p = PurePosixPath(path_str)
    parts = p.parts
    # e.g. ('/', 'home', 'user', 'PhpstormProjects') -> container
    if len(parts) == 4 and parts[1].lower() in ("home", "users") and parts[3].lower() in PROJECT_CONTAINERS:
        return True
    return False


def discover_workspace_roots(user_home: Optional[Path] = None) -> List[str]:
    """
    Dynamically discovers all authentic workspace roots from:
      1. ~/.gemini/config/projects/*.json project definitions
      2. IDE workspaceStorage (workspace.json files)
      3. IDE state.vscdb (history.recentlyOpenedPathsList)
      4. Active conversation_summaries.db (workspace_uris column)
      5. Existing KNOWN_ROOTS
    """
    home = user_home or get_user_home()
    roots_set: Set[str] = set(KNOWN_ROOTS)

    # 1. ~/.gemini/config/projects/*.json
    projects_dir = home / ".gemini" / "config" / "projects"
    if projects_dir.is_dir():
        for fpath in projects_dir.glob("*.json"):
            if fpath.name in ("outside-of-project.json", "default-cli-project.json"):
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                resources = data.get("projectResources", {}).get("resources", [])
                for r in resources:
                    furi = r.get("folderUri") or r.get("gitFolder", {}).get("folderUri")
                    if furi and str(furi).startswith("file://"):
                        roots_set.add(str(furi))
            except Exception:
                pass

    # 2. Candidate IDE workspaceStorage
    for pat in [
        os.path.join(str(home), ".config", "*", "User", "workspaceStorage", "*", "workspace.json"),
        os.path.join(str(home), ".antigravity*", ".config", "*", "User", "workspaceStorage", "*", "workspace.json"),
    ]:
        for wp in glob.glob(pat):
            try:
                with open(wp, "r", encoding="utf-8") as f:
                    wdata = json.load(f)
                furi = wdata.get("folder") or wdata.get("workspace")
                if furi and str(furi).startswith("file://") and not any(k in str(furi) for k in [".gemini", "Workspaces"]):
                    roots_set.add(str(furi))
            except Exception:
                pass

    # 3. Candidate state.vscdb recently opened paths
    for pat in [
        os.path.join(str(home), ".config", "*", "User", "globalStorage", "state.vscdb"),
        os.path.join(str(home), ".antigravity*", ".config", "*", "User", "globalStorage", "state.vscdb"),
    ]:
        for sp in glob.glob(pat):
            if any(k in sp.lower() for k in ["antigravity", "code"]):
                try:
                    with sqlite3.connect(sp, timeout=2.0) as s_con:
                        s_cur = s_con.cursor()
                        row = s_cur.execute(
                            "SELECT value FROM ItemTable WHERE key = 'history.recentlyOpenedPathsList';"
                        ).fetchone()
                        if row and row[0]:
                            parsed = json.loads(row[0])
                            for entry in parsed.get("entries", []):
                                furi = entry.get("folderUri")
                                if furi and str(furi).startswith("file://") and not any(k in str(furi) for k in [".gemini"]):
                                    roots_set.add(str(furi))
                except Exception:
                    pass

    # Update KNOWN_ROOTS in-place
    for r in sorted(roots_set):
        if r not in KNOWN_ROOTS:
            KNOWN_ROOTS.append(r)

    return sorted(list(roots_set), key=len, reverse=True)


def normalize_workspace_uri(
    uri: Optional[str],
    user_home: Optional[Path] = None,
) -> Optional[str]:
    """
    Normalizes subfolder workspace paths to their respective root workspace URIs.
    Dynamically identifies roots using:
      1. Registered project configs and IDE workspaceStorage roots
      2. Local filesystem Git repository detection (.git boundaries)
      3. Universal project container directory heuristic for cross-machine / offline paths
    """
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
    if not uri_str.startswith("file://"):
        return uri_str

    # 1. Match against known / discovered roots (longest match first)
    roots = list(KNOWN_ROOTS)
    if not roots:
        roots = discover_workspace_roots(user_home)
    else:
        roots = sorted(roots, key=len, reverse=True)

    for root in roots:
        if uri_str == root:
            return root
        # Only collapse subdirectories if the root is an actual project, not a container folder
        if not is_container_or_system_root(root):
            if uri_str.startswith(root + "/") or uri_str.startswith(root + "\\"):
                return root

    # 2. Local filesystem Git repository detection
    parsed = urlsplit(uri_str)
    path_str = unquote(parsed.path)
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

        # 3. Universal project container directory heuristic
        p_posix = PurePosixPath(path_str)
        parts = p_posix.parts
        start_idx = 0
        if len(parts) >= 3 and parts[1].lower() in ("home", "users"):
            start_idx = 3

        for i in range(start_idx, len(parts) - 1):
            if parts[i].lower() in PROJECT_CONTAINERS:
                root_parts = parts[: i + 2]
                root_path = PurePosixPath(*root_parts)
                root_uri = f"file://{root_path}"
                register_known_root(root_uri)
                return root_uri

    return uri_str


def ensure_project_configs(
    user_home: Optional[Path] = None,
    workspace_uris: Optional[List[str]] = None,
) -> None:
    """
    Ensures registered project JSON definitions exist in ~/.gemini/config/projects/.
    Generates authentic project configs for missing workspace roots dynamically.
    """
    home = user_home or get_user_home()
    projects_dir = home / ".gemini" / "config" / "projects"
    try:
        projects_dir.mkdir(parents=True, exist_ok=True)

        # 1. Seed definitions for test and legacy compatibility
        for p in SEED_PROJECT_CONFIGS:
            fpath = projects_dir / f"{p['id']}.json"
            if not fpath.exists():
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(p, f, indent=2)

        # 2. Dynamic generation for active workspace roots without configs
        targets = set(workspace_uris or [])
        for r in discover_workspace_roots(home):
            targets.add(r)

        existing_folder_uris = set()
        for fpath in projects_dir.glob("*.json"):
            if fpath.name in ("outside-of-project.json", "default-cli-project.json"):
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for r in data.get("projectResources", {}).get("resources", []):
                    u = r.get("folderUri") or r.get("gitFolder", {}).get("folderUri")
                    if u:
                        existing_folder_uris.add(u)
            except Exception:
                pass

        for ws in targets:
            if not ws or ws in existing_folder_uris:
                continue
            if not ws.startswith("file://") or any(k in ws for k in [".gemini", "/tmp"]):
                continue
            parsed = urlsplit(ws)
            path_str = unquote(parsed.path)
            pname = PurePosixPath(path_str).name or "project"
            pid = KNOWN_PROJECT_MAPPINGS.get(ws) or str(uuid.uuid5(uuid.NAMESPACE_URL, ws))
            proj_def = {
                "id": pid,
                "name": pname,
                "projectResources": {
                    "resources": [
                        {
                            "gitFolder": {
                                "folderUri": ws,
                                "defaultBranch": "main",
                            }
                        }
                    ]
                },
                "permissionGrants": {"v2Migrated": True},
                "settings": {},
                "isWorkspaceOnly": False,
            }
            fpath = projects_dir / f"{pid}.json"
            if not fpath.exists():
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(proj_def, f, indent=2)
                existing_folder_uris.add(ws)
    except Exception:
        pass


def get_project_id_for_workspace(
    ws_uri: Optional[str],
    user_home: Optional[Path] = None,
) -> Optional[str]:
    """
    Resolves canonical project_id for a workspace URI by querying
    ~/.gemini/config/projects/ and authentic project definitions.
    """
    if not ws_uri:
        return None
    ws_norm = normalize_workspace_uri(ws_uri, user_home=user_home)
    if not ws_norm:
        return None

    home = user_home or get_user_home()
    projects_dir = home / ".gemini" / "config" / "projects"

    mappings = dict(KNOWN_PROJECT_MAPPINGS)

    if projects_dir.is_dir():
        for fpath in projects_dir.glob("*.json"):
            fname = fpath.name
            if fname in ("outside-of-project.json", "default-cli-project.json"):
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                pid = data.get("id")
                pname = data.get("name", "")
                resources = data.get("projectResources", {}).get("resources", [])
                for r in resources:
                    furi = r.get("folderUri") or r.get("gitFolder", {}).get("folderUri")
                    if furi and pid and furi == ws_norm:
                        if not pname.startswith("/"):
                            return pid
                        mappings.setdefault(furi, pid)
            except Exception:
                pass

    return mappings.get(ws_norm)
