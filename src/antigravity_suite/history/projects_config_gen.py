"""
Automatic Project Configuration Generation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote, urlsplit

from antigravity_suite.config import get_user_home
from antigravity_suite.history.projects_roots import get_candidate_gemini_dirs
from antigravity_suite.history.projects_validator import is_container_or_system_root


def ensure_project_configs(
    user_home: Optional[Path] = None,
    workspace_uris: Optional[List[str]] = None,
) -> None:
    """Ensures authentic project JSON definitions exist in config/projects/."""
    from antigravity_suite.history.projects_resolver import get_project_id_for_workspace

    home = user_home or get_user_home()
    gdirs = get_candidate_gemini_dirs(home)
    if not gdirs:
        return
    targets = set(workspace_uris) if workspace_uris is not None else set()

    for gdir in gdirs:
        p_dir = gdir / "config" / "projects"
        try:
            p_dir.mkdir(parents=True, exist_ok=True)
            existing = set()
            for fpath in p_dir.glob("*.json"):
                if fpath.name in ("outside-of-project.json", "default-cli-project.json"):
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        for r in json.load(f).get("projectResources", {}).get("resources", []):
                            u = r.get("folderUri") or r.get("gitFolder", {}).get("folderUri")
                            if u:
                                existing.add(u)
                except Exception:
                    pass

            for ws in targets:
                if not ws or ws in existing or not ws.startswith("file://") or ".gemini" in ws or is_container_or_system_root(ws, user_home=home):
                    continue
                clean_path = unquote(urlsplit(ws).path).replace("\\", "/").rstrip("/")
                if workspace_uris is None and not (Path(clean_path) / ".git").exists():
                    continue
                pname = clean_path.split("/")[-1] if clean_path else "project"
                pid = get_project_id_for_workspace(ws, user_home=home, create_missing=True)
                proj_def = {
                    "id": pid, "name": pname,
                    "projectResources": {"resources": [{"gitFolder": {"folderUri": ws, "defaultBranch": "main"}}]},
                    "permissionGrants": {"v2Migrated": True}, "settings": {}, "isWorkspaceOnly": False,
                }
                fpath = p_dir / f"{pid}.json"
                if not fpath.exists():
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump(proj_def, f, indent=2)
                    existing.add(ws)
        except Exception:
            pass
