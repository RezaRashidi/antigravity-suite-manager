"""
Projects Order Synchronization Across Profiles.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Set, Tuple


def replicate_projects_order(
    user_home: Optional[Path] = None,
    extra_project_ids: Optional[Set[str]] = None,
) -> None:
    """Synchronizes projectsOrder across all discovered app_storage.json files."""
    home = Path(user_home).resolve() if user_home else Path.home().resolve()
    candidate_app_storages = [home / ".config" / "Antigravity" / "app_storage.json"] + list(
        home.glob(".antigravity-profile*/.config/Antigravity/app_storage.json")
    )
    all_known_projects: Set[str] = set(extra_project_ids or [])

    for gdir in [home / ".gemini", home / ".gemide"] + list(home.glob(".antigravity-profile*/.gemini")):
        for pjson in (gdir / "config" / "projects").glob("*.json"):
            stem = pjson.stem.strip()
            if stem and stem not in ("outside-of-project", "default-cli-project"):
                all_known_projects.add(stem)

    loaded_storages: List[Tuple[Path, dict, List[str], bool]] = []
    for app_store in [p for p in candidate_app_storages if p.is_file()]:
        try:
            with open(app_store, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_val = data.get("projectsOrder", [])
            was_str = isinstance(raw_val, str)
            existing = json.loads(raw_val) if was_str else (raw_val if isinstance(raw_val, list) else [])
            all_known_projects.update(existing)
            loaded_storages.append((app_store, data, existing, was_str))
        except Exception:
            pass

    if not all_known_projects:
        return

    for app_store, data, existing, was_str in loaded_storages:
        try:
            merged = list(existing)
            for pid in sorted(all_known_projects):
                if pid not in merged:
                    merged.append(pid)
            if merged != existing:
                data["projectsOrder"] = json.dumps(merged) if was_str else merged
                with open(app_store, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
        except Exception:
            pass
