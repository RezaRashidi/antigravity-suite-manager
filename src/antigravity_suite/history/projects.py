"""
Project Mapping and Configuration Manager for Antigravity Suite.

Maps workspace URIs to authentic project UUIDs registered in
~/.gemini/config/projects/ so conversations group correctly in Desktop App and IDE.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from antigravity_suite.config import get_user_home


KNOWN_ROOTS: List[str] = [
    "file:///home/reza/PhpstormProjects/Odirect",
    "file:///home/reza/Music/lede",
    "file:///home/reza/PhpstormProjects/k6",
    "file:///home/reza/Library/nokia_modem",
    "file:///home/reza/Music/irankhodro",
    "file:///home/reza/PhpstormProjects/api",
    "file:///home/reza/Downloads/cloudflare",
    "file:///home/reza/Downloads/dragonfly-ansible-main",
    "file:///home/reza/Downloads/minio-ansible-main",
    "file:///home/reza/.config/mihomo-party/profiles",
    "file:///home/reza/Documents/nokia",
    "file:///home/reza/.antigravity-suite-manager",
]

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


def normalize_workspace_uri(uri: Optional[str]) -> Optional[str]:
    """Normalizes subfolder workspace paths to their respective root workspace URIs."""
    if not uri:
        return None
    uri_str = str(uri).strip()
    if uri_str.startswith("["):
        try:
            arr = json.loads(uri_str)
            if arr:
                uri_str = arr[0]
        except Exception:
            pass
    if not uri_str.startswith("file://"):
        return uri_str

    for root in KNOWN_ROOTS:
        if uri_str == root or uri_str.startswith(root + "/") or uri_str.startswith(root + "\\"):
            return root
    return uri_str


def ensure_project_configs(user_home: Optional[Path] = None) -> None:
    """Ensures registered project JSON definitions exist in ~/.gemini/config/projects/."""
    home = user_home or get_user_home()
    projects_dir = home / ".gemini" / "config" / "projects"
    try:
        projects_dir.mkdir(parents=True, exist_ok=True)
        extra_projects = [
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
        for p in extra_projects:
            fpath = projects_dir / f"{p['id']}.json"
            if not fpath.exists():
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(p, f, indent=2)
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
    ws_norm = normalize_workspace_uri(ws_uri)
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
