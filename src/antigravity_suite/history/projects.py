"""
Project Mapping and Configuration Manager for Antigravity Suite.

Maps workspace URIs to authentic project UUIDs registered in
~/.gemini/config/projects/ so conversations group correctly in Desktop App and IDE.
Dynamically detects workspace roots and project IDs without hardcoding machine-specific paths or mappings.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3
import time
import uuid
from functools import lru_cache
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

# Dynamic runtime cache of workspace-to-project-id mappings
KNOWN_PROJECT_MAPPINGS: Dict[str, str] = {}


def register_known_root(root_uri: str) -> None:
    """Registers a root workspace URI into the active KNOWN_ROOTS cache."""
    if root_uri and root_uri not in KNOWN_ROOTS:
        KNOWN_ROOTS.append(root_uri)
        try:
            normalize_workspace_uri.cache_clear()
        except Exception:
            pass


def register_project_mapping(workspace_uri: str, project_id: str) -> None:
    """Registers a workspace-to-project-id mapping in the active runtime cache."""
    if workspace_uri and project_id:
        KNOWN_PROJECT_MAPPINGS[workspace_uri] = project_id


@lru_cache(maxsize=2048)
def is_container_or_system_root(uri_str: str) -> bool:
    """
    Returns True if uri_str is a parent container folder or system root
    (e.g. /tmp, /var/tmp, /home/<user>, /home/<user>/PhpstormProjects) that
    should NOT swallow sub-projects.
    """
    if not uri_str:
        return True
    parsed = urlsplit(uri_str)
    path_str = unquote(parsed.path).replace("\\", "/").rstrip("/")
    if path_str in ("/tmp", "/var/tmp", "/home", "/Users", "") or path_str.count("/") <= 2:
        return True
    parts = path_str.split("/")
    if len(parts) == 4 and parts[1].lower() in ("home", "users") and parts[3].lower() in PROJECT_CONTAINERS:
        return True
    if len(parts) >= 2 and parts[-1].lower() in PROJECT_CONTAINERS and not (Path(path_str) / ".git").exists():
        return True
    return False


@lru_cache(maxsize=2048)
def is_valid_workspace_uri(
    uri: Optional[str],
    user_home: Optional[Path] = None,
) -> bool:
    """
    Validates if a workspace URI is syntactically well-formed, points to an
    actual project directory, and does not refer to non-existent local paths
    or system container roots.
    """
    if not uri or not isinstance(uri, str):
        return False
    u = uri.strip().rstrip("`\"';,")
    if not u.startswith("file://"):
        return False
    if any(c in u for c in ("\n", "\r", "`", "<", ">", '"', "'")):
        return False
    if any(k in u for k in ("outside-of-project", ".gemini/antigravity/brain", ".config/Antigravity")):
        return False

    parsed = urlsplit(u)
    path_str = unquote(parsed.path)
    if not path_str or path_str in ("/", "\\"):
        return False

    # Container or system roots alone are not authentic project workspaces
    if is_container_or_system_root(u):
        return False

    home = (user_home or get_user_home()).resolve()
    p = Path(path_str)
    try:
        if str(home) in path_str:
            return p.is_dir()
        if p.exists():
            return p.is_dir()
    except Exception:
        pass

    return True


def get_candidate_gemini_dirs(user_home: Optional[Path] = None) -> List[Path]:
    """
    Returns candidate Antigravity root directories across Hub (~/.gemini),
    IDE (~/.gemide, ~/.gemini-ide), and custom profiles.
    """
    home = user_home or get_user_home()
    candidates: List[Path] = []
    env_dir = os.environ.get("ANTIGRAVITY_GEMINI_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    candidates.extend([
        home / ".gemini",
        home / ".gemide",
        home / ".gemini-ide",
        home / ".antigravity-profile2" / ".gemini",
    ])

    for p_glob in [
        home / ".antigravity-profile-app-*" / ".gemini",
        home / ".antigravity-ide-profile-*" / ".gemini",
    ]:
        for match in glob.glob(str(p_glob)):
            candidates.append(Path(match))

    seen = set()
    valid = []
    for c in candidates:
        try:
            res = c.resolve()
            if res.is_dir() and str(res) not in seen:
                seen.add(str(res))
                valid.append(c)
        except Exception:
            pass
    if not valid:
        valid = [home / ".gemini"]
    return valid


def discover_workspace_roots(user_home: Optional[Path] = None) -> List[str]:
    """
    Dynamically discovers all authentic workspace roots from:
      1. Registered project definitions in ~/.gemini/config/projects/ and ~/.gemide/config/projects/
      2. IDE workspaceStorage (workspace.json files)
      3. IDE state.vscdb (history.recentlyOpenedPathsList)
      4. Active conversation_summaries.db (workspace_uris column)
      5. Existing KNOWN_ROOTS
    """
    home = user_home or get_user_home()
    roots_set: Set[str] = set(KNOWN_ROOTS)

    # 1. Candidate project configs (~/.gemini/config/projects/, ~/.gemide/config/projects/)
    for gdir in get_candidate_gemini_dirs(home):
        projects_dir = gdir / "config" / "projects"
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

    # 2. Candidate Antigravity IDE workspaceStorage only
    for pat in [
        os.path.join(str(home), ".config", "Antigravity*", "User", "workspaceStorage", "*", "workspace.json"),
        os.path.join(str(home), ".config", "antigravity*", "User", "workspaceStorage", "*", "workspace.json"),
        os.path.join(str(home), ".antigravity*", "User", "workspaceStorage", "*", "workspace.json"),
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

    # Update KNOWN_ROOTS in-place
    for r in sorted(roots_set):
        if r not in KNOWN_ROOTS:
            KNOWN_ROOTS.append(r)

    return sorted(list(roots_set), key=len, reverse=True)


@lru_cache(maxsize=1024)
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
    uri_str = uri_str.rstrip("`\"';,")
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
        clean_path = path_str.replace("\\", "/")
        parts = clean_path.split("/")
        start_idx = 0
        if len(parts) >= 3 and parts[1].lower() in ("home", "users"):
            start_idx = 3

        for i in range(start_idx, len(parts) - 1):
            if parts[i].lower() in PROJECT_CONTAINERS:
                root_path = "/".join(parts[: i + 2])
                root_uri = f"file://{root_path}"
                register_known_root(root_uri)
                return root_uri

    return uri_str


_PROJECT_MAPPINGS_CACHE: Optional[Dict[str, str]] = None
_LAST_MAPPINGS_DISCOVERY_TIME: float = 0.0


def clear_workspace_caches() -> None:
    """Clears workspace normalization and project mapping runtime caches."""
    global _PROJECT_MAPPINGS_CACHE, _LAST_MAPPINGS_DISCOVERY_TIME
    _PROJECT_MAPPINGS_CACHE = None
    _LAST_MAPPINGS_DISCOVERY_TIME = 0.0
    is_container_or_system_root.cache_clear()
    is_valid_workspace_uri.cache_clear()
    normalize_workspace_uri.cache_clear()


def discover_project_mappings(
    user_home: Optional[Path] = None,
    force_refresh: bool = False,
    cache_ttl: float = 60.0,
) -> Dict[str, str]:
    """
    Dynamically discovers all project mappings across all active instances:
      1. Registered JSON project files in ~/.gemini/config/projects/ and ~/.gemide/config/projects/
      2. Active conversation_summaries.db (workspace_uris -> project_id) across Hub and IDE
      3. Existing runtime KNOWN_PROJECT_MAPPINGS
    Caches results in-memory with automatic TTL and force_refresh support.
    """
    global _PROJECT_MAPPINGS_CACHE, _LAST_MAPPINGS_DISCOVERY_TIME
    now = time.time()
    if not force_refresh and _PROJECT_MAPPINGS_CACHE is not None and (now - _LAST_MAPPINGS_DISCOVERY_TIME) < cache_ttl:
        return dict(_PROJECT_MAPPINGS_CACHE)

    home = user_home or get_user_home()
    mappings: Dict[str, str] = dict(KNOWN_PROJECT_MAPPINGS)

    for gdir in get_candidate_gemini_dirs(home):
        # 1. Read authentic project definitions in config/projects/
        projects_dir = gdir / "config" / "projects"
        if projects_dir.is_dir():
            for fpath in projects_dir.glob("*.json"):
                if fpath.name in ("outside-of-project.json", "default-cli-project.json"):
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    pid = data.get("id")
                    pname = data.get("name", "")
                    resources = data.get("projectResources", {}).get("resources", [])
                    for r in resources:
                        furi = r.get("folderUri") or r.get("gitFolder", {}).get("folderUri")
                        if furi and pid and str(furi).startswith("file://"):
                            if furi not in mappings or not pname.startswith("/"):
                                mappings[str(furi)] = str(pid)
                except Exception:
                    pass

        # 2. Read previous authentic associations from conversation_summaries.db
        for sub in ["antigravity", "antigravity-ide", ""]:
            db_path = (gdir / sub / "conversation_summaries.db") if sub else (gdir / "conversation_summaries.db")
            if db_path.is_file():
                try:
                    with sqlite3.connect(db_path, timeout=2.0) as con:
                        cur = con.cursor()
                        for row in cur.execute(
                            "SELECT DISTINCT workspace_uris, project_id FROM conversation_summaries "
                            "WHERE workspace_uris IS NOT NULL AND workspace_uris != '' "
                            "AND project_id IS NOT NULL AND project_id != '' "
                            "AND project_id != 'outside-of-project';"
                        ):
                            raw_ws, pid = row[0], row[1]
                            norm_ws = normalize_workspace_uri(raw_ws, user_home=home)
                            if norm_ws and pid and norm_ws not in mappings:
                                if is_valid_workspace_uri(norm_ws, user_home=home):
                                    mappings[norm_ws] = str(pid)
                except Exception:
                    pass

    # Update runtime caches in-place
    KNOWN_PROJECT_MAPPINGS.update(mappings)
    _PROJECT_MAPPINGS_CACHE = dict(mappings)
    _LAST_MAPPINGS_DISCOVERY_TIME = now
    return mappings


def ensure_project_configs(
    user_home: Optional[Path] = None,
    workspace_uris: Optional[List[str]] = None,
) -> None:
    """
    Ensures authentic project JSON definitions exist in config/projects/.
    Generates authentic project configs for missing workspace roots dynamically.
    """
    home = user_home or get_user_home()
    gdirs = get_candidate_gemini_dirs(home)
    if not gdirs:
        return

    if workspace_uris is not None:
        targets = set(workspace_uris)
    else:
        targets = set()

    for gdir in gdirs:
        projects_dir = gdir / "config" / "projects"
        try:
            projects_dir.mkdir(parents=True, exist_ok=True)

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
                if not ws.startswith("file://") or any(k in ws for k in [".gemini", "/tmp"]) or is_container_or_system_root(ws):
                    continue
                parsed = urlsplit(ws)
                path_str = unquote(parsed.path)
                clean_path = path_str.replace("\\", "/").rstrip("/")
                # If workspace_uris was not explicitly provided, only auto-create config for genuine Git repositories
                if workspace_uris is None and not (Path(clean_path) / ".git").exists():
                    continue
                pname = clean_path.split("/")[-1] if clean_path else "project"
                pid = get_project_id_for_workspace(ws, user_home=home, create_missing=True)
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
    mappings: Optional[Dict[str, str]] = None,
    create_missing: bool = False,
) -> Optional[str]:
    """
    Resolves canonical project_id for a workspace URI dynamically:
      1. Uses pre-discovered or cached project mappings (O(1))
      2. Resolves subfolder to normalized root project
      3. Performs lazy refresh on cache miss before fallback
      4. Returns None if unregistered, preventing phantom UUID generation
    """
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

    if ws_norm in KNOWN_PROJECT_MAPPINGS:
        return KNOWN_PROJECT_MAPPINGS[ws_norm]

    # Lazy refresh check on cache miss in case a new project was registered on disk
    refreshed = discover_project_mappings(home, force_refresh=True)
    if ws_norm in refreshed:
        mappings[ws_norm] = refreshed[ws_norm]
        return refreshed[ws_norm]

    if not create_missing:
        return None

    # Generate a deterministic UUID5 for authentic, stable project identification
    deterministic_id = str(uuid.uuid5(uuid.NAMESPACE_URL, ws_norm))
    mappings[ws_norm] = deterministic_id
    KNOWN_PROJECT_MAPPINGS[ws_norm] = deterministic_id
    if _PROJECT_MAPPINGS_CACHE is not None:
        _PROJECT_MAPPINGS_CACHE[ws_norm] = deterministic_id
    return deterministic_id


def get_workspace_for_project_id(
    project_id: Optional[str],
    user_home: Optional[Path] = None,
) -> Optional[str]:
    """
    Resolves the canonical workspace URI for a given project UUID:
      1. Reads authentic project configuration from ~/.gemini/config/projects/{project_id}.json
      2. Scans other candidate gemini config/projects directories
      3. Checks runtime project mappings for a registered workspace
    """
    if not project_id or str(project_id).strip() in ("outside-of-project", "default-cli-project"):
        return None

    home = user_home or get_user_home()
    clean_pid = str(project_id).strip()

    # 1. Search authentic project definitions in config/projects/
    for gdir in get_candidate_gemini_dirs(home):
        projects_dir = gdir / "config" / "projects"
        if not projects_dir.is_dir():
            continue
        p_file = projects_dir / f"{clean_pid}.json"
        if p_file.is_file():
            try:
                with open(p_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                resources = data.get("projectResources", {}).get("resources", [])
                for r in resources:
                    furi = r.get("folderUri") or r.get("gitFolder", {}).get("folderUri")
                    if furi and str(furi).startswith("file://"):
                        return str(furi).strip().rstrip("`\"';,")
            except Exception:
                pass

    # 2. Check KNOWN_PROJECT_MAPPINGS reverse lookup
    for ws, pid in KNOWN_PROJECT_MAPPINGS.items():
        if pid == clean_pid and ws.startswith("file://"):
            return ws

    return None

