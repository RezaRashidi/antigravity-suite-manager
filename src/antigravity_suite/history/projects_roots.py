"""
Gemini Directory and Workspace Root Discovery.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import List, Optional, Set

from antigravity_suite.config import get_user_home
from antigravity_suite.history.projects_constants import KNOWN_ROOTS


def get_candidate_gemini_dirs(user_home: Optional[Path] = None) -> List[Path]:
    """Returns candidate Antigravity root directories across Hub, IDE, and custom profiles."""
    home = user_home or get_user_home()
    candidates: List[Path] = []
    env_dir = os.environ.get("ANTIGRAVITY_GEMINI_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    candidates.extend([
        home / ".gemini", home / ".gemide", home / ".gemini-ide", home / ".antigravity-profile2" / ".gemini",
    ])
    for p_glob in [home / ".antigravity-profile-app-*" / ".gemini", home / ".antigravity-ide-profile-*" / ".gemini"]:
        for match in glob.glob(str(p_glob)):
            candidates.append(Path(match))

    seen, valid = set(), []
    for c in candidates:
        try:
            res = c.resolve()
            if res.is_dir() and str(res) not in seen:
                seen.add(str(res))
                valid.append(c)
        except Exception:
            pass
    return valid or [home / ".gemini"]


def discover_workspace_roots(user_home: Optional[Path] = None) -> List[str]:
    """Dynamically discovers all authentic workspace roots."""
    home = user_home or get_user_home()
    roots_set: Set[str] = set(KNOWN_ROOTS)

    for gdir in get_candidate_gemini_dirs(home):
        projects_dir = gdir / "config" / "projects"
        if projects_dir.is_dir():
            for fpath in projects_dir.glob("*.json"):
                if fpath.name in ("outside-of-project.json", "default-cli-project.json"):
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for r in data.get("projectResources", {}).get("resources", []):
                        furi = r.get("folderUri") or r.get("gitFolder", {}).get("folderUri")
                        if furi and str(furi).startswith("file://"):
                            roots_set.add(str(furi))
                except Exception:
                    pass

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

    for r in sorted(roots_set):
        if r not in KNOWN_ROOTS:
            KNOWN_ROOTS.append(r)
    return sorted(list(roots_set), key=len, reverse=True)
