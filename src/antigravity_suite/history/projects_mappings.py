"""
Project Mappings Discovery from Configs and SQLite Summaries.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Optional

from antigravity_suite.config import get_user_home
import antigravity_suite.history.projects_constants as pc
from antigravity_suite.history.projects_normalize import normalize_workspace_uri
from antigravity_suite.history.projects_roots import get_candidate_gemini_dirs
from antigravity_suite.history.projects_validator import is_valid_workspace_uri


def discover_project_mappings(
    user_home: Optional[Path] = None,
    force_refresh: bool = False,
    cache_ttl: float = 60.0,
) -> Dict[str, str]:
    """Dynamically discovers all workspace-to-project-id mappings across active profiles."""
    now = time.time()
    if not force_refresh and pc._PROJECT_MAPPINGS_CACHE is not None and (now - pc._LAST_MAPPINGS_DISCOVERY_TIME) < cache_ttl:
        return dict(pc._PROJECT_MAPPINGS_CACHE)

    home = user_home or get_user_home()
    mappings: Dict[str, str] = dict(pc.KNOWN_PROJECT_MAPPINGS)

    for gdir in get_candidate_gemini_dirs(home):
        projects_dir = gdir / "config" / "projects"
        if projects_dir.is_dir():
            for fpath in projects_dir.glob("*.json"):
                if fpath.name in ("outside-of-project.json", "default-cli-project.json"):
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    pid, pname = data.get("id"), data.get("name", "")
                    for r in data.get("projectResources", {}).get("resources", []):
                        furi = r.get("folderUri") or r.get("gitFolder", {}).get("folderUri")
                        if furi and pid and str(furi).startswith("file://") and (furi not in mappings or not pname.startswith("/")):
                            mappings[str(furi)] = str(pid)
                except Exception:
                    pass

        for sub in ["antigravity", "antigravity-ide", ""]:
            db_path = (gdir / sub / "conversation_summaries.db") if sub else (gdir / "conversation_summaries.db")
            if db_path.is_file():
                try:
                    with sqlite3.connect(db_path, timeout=2.0) as con:
                        for row in con.cursor().execute(
                            "SELECT DISTINCT workspace_uris, project_id FROM conversation_summaries "
                            "WHERE workspace_uris IS NOT NULL AND workspace_uris != '' "
                            "AND project_id IS NOT NULL AND project_id != '' AND project_id != 'outside-of-project';"
                        ):
                            norm_ws = normalize_workspace_uri(row[0], user_home=home)
                            if norm_ws and row[1] and norm_ws not in mappings and is_valid_workspace_uri(norm_ws, user_home=home):
                                mappings[norm_ws] = str(row[1])
                except Exception:
                    pass

    pc.KNOWN_PROJECT_MAPPINGS.update(mappings)
    pc._PROJECT_MAPPINGS_CACHE = dict(mappings)
    pc._LAST_MAPPINGS_DISCOVERY_TIME = now
    return mappings
