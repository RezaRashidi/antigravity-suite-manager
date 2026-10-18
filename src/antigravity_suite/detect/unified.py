"""
Unified aggregator for instances and engine installations.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from antigravity_suite.detect.clones_scan import scan_clones
from antigravity_suite.detect.inspectors import inspect_app_dir, inspect_ide_dir
from antigravity_suite.detect.launchers import get_launcher_binary, update_launcher_binary
from antigravity_suite.detect.paths_config import load_paths_config
from antigravity_suite.detect.scan import scan_installations


def get_unified_instances() -> Tuple[List[Dict[str, Any]], str, str, List[str]]:
    engines = scan_installations()
    engines_by_path = {os.path.realpath(eng["path"]): eng for eng in engines}
    first_app = next((e["path"] for e in engines if "App" in e["type"] or "Manager" in e["type"]), "")
    first_ide = next((e["path"] for e in engines if "IDE" in e["type"]), "")

    curr_app, curr_ide, custom_paths = load_paths_config(first_app, first_ide)
    if (not curr_app or not os.path.isdir(curr_app)) and first_app: curr_app = first_app
    if (not curr_ide or not os.path.isdir(curr_ide)) and first_ide: curr_ide = first_ide

    clones = scan_clones(curr_app, curr_ide)
    unified: List[Dict[str, Any]] = []

    for c in clones:
        launcher_f = c["launcher"]
        linked_bin = get_launcher_binary(launcher_f) if (launcher_f and os.path.isfile(launcher_f)) else ""
        eng = None
        if linked_bin and os.path.isfile(linked_bin):
            eng_dir = os.path.realpath(os.path.dirname(linked_bin))
            if os.path.basename(eng_dir) in ["bin", "MacOS"]:
                eng_dir = os.path.dirname(eng_dir)
            eng = engines_by_path.get(eng_dir) or inspect_ide_dir(eng_dir) or inspect_app_dir(eng_dir)
            if eng: engines_by_path[eng_dir] = eng

        if not eng:
            target_p = curr_ide if "IDE" in c["type"] else curr_app
            eng = engines_by_path.get(os.path.realpath(target_p)) if target_p else None
            if not eng and target_p and os.path.isdir(target_p):
                eng = inspect_ide_dir(os.path.realpath(target_p)) if "IDE" in c["type"] else inspect_app_dir(os.path.realpath(target_p))

        eng_p = eng["path"] if eng else (curr_ide if "IDE" in c["type"] else curr_app)
        eng_v = eng["version"] if eng else "Unknown"

        if launcher_f and os.path.isfile(launcher_f):
            if (not linked_bin or not os.path.isfile(linked_bin)) and eng and eng.get("executable") and os.path.isfile(eng["executable"]):
                update_launcher_binary(launcher_f, eng["executable"])

        if not eng and not os.path.isfile(launcher_f) and not os.path.isdir(eng_p):
            continue

        unified.append({
            "kind": "instance", "clone": c, "engine": eng, "name": c["name"], "type": c["type"],
            "version": eng_v, "engine_path": eng_p, "history_mode": c["history_mode"],
            "keyring_mode": c["keyring_mode"], "launcher": c["launcher"], "status": c["status"],
        })

    used_paths = {os.path.realpath(u["engine_path"]) for u in unified if u.get("engine_path") and os.path.isdir(u.get("engine_path"))}
    for eng in engines:
        if os.path.realpath(eng["path"]) not in used_paths:
            unified.append({
                "kind": "engine", "clone": None, "engine": eng, "name": f"{eng['type']} (Standalone Engine)",
                "type": eng["type"], "version": eng["version"], "engine_path": eng["path"],
                "history_mode": "N/A", "keyring_mode": "Normal", "launcher": eng.get("executable", ""), "status": "Installed",
            })

    def sort_order(item: Dict[str, Any]) -> int:
        cid = item.get("clone", {}).get("id", "") if item.get("clone") else ""
        return {"ide1": 0, "app1": 1, "app2": 2}.get(cid, 3 if cid.startswith("app-") else (4 if cid.startswith("ide-") else 5))

    unified.sort(key=sort_order)
    return unified, curr_app, curr_ide, custom_paths
