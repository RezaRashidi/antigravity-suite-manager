"""
Filesystem and system path scanning for Antigravity installations.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Set

from antigravity_suite.detect.constants import BLUE, BOLD, CYAN, GREEN, NC, RED, YELLOW
from antigravity_suite.detect.inspectors import inspect_app_dir, inspect_ide_dir
from antigravity_suite.detect.scan_candidates import get_scan_candidates


def scan_installations() -> List[Dict[str, Any]]:
    candidates = get_scan_candidates()
    installations: List[Dict[str, Any]] = []
    seen_paths: Set[str] = set()

    for c in sorted(candidates):
        real_c = os.path.realpath(c)
        if real_c in seen_paths or "manager" in real_c.lower():
            continue
        ide = inspect_ide_dir(real_c)
        if ide:
            installations.append(ide)
            seen_paths.add(real_c)
            continue
        app = inspect_app_dir(real_c)
        if app:
            installations.append(app)
            seen_paths.add(real_c)
            continue
    return installations


def print_table(installs: List[Dict[str, Any]]) -> None:
    print(f"{CYAN}========================================================================================{NC}")
    print(f"{BOLD}{CYAN}                    Detected Antigravity Installations on System                       {NC}")
    print(f"{CYAN}========================================================================================{NC}")
    if not installs:
        print(f"{RED}No Antigravity installations found on this system.{NC}")
        print(f"{YELLOW}Run 'manage-antigravity.sh install' to install Antigravity App and IDE.{NC}")
        print(f"{CYAN}========================================================================================{NC}")
        return
    print(f"{BOLD}{BLUE}Type                 Version     Writable    Executable                  Path{NC}")
    print(f"----------------------------------------------------------------------------------------")
    for item in installs:
        t, v = item["type"], f"v{item['version']}" if item["version"] != "Unknown" else "Unknown"
        w = f"{GREEN}Yes{NC}" if item["writable"] else f"{RED}No (Root){NC}"
        exe_base = os.path.basename(item["executable"]) if item["executable"] else f"{RED}None{NC}"
        print(f"{t:<20} {v:<11} {w:<20} {exe_base:<27} {item['path']}")
    print(f"{CYAN}========================================================================================{NC}")
