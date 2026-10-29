"""
Control Center Overview Terminal Rendering Engine.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List
from antigravity_suite.detect.constants import BLUE, BOLD, CYAN, GREEN, NC, YELLOW


def render_control_center_overview(unified: List[Dict[str, Any]]) -> None:
    print(f"\n{CYAN}========================================================================================{NC}")
    print(f"{BOLD}{CYAN}                     Antigravity Suite Manager - Control Center                         {NC}")
    print(f"{CYAN}========================================================================================{NC}")
    print(f"{BOLD}{BLUE}[ DETECTED ANTIGRAVITY SUITE INSTANCES ({len(unified)}) ]{NC}")
    print("----------------------------------------------------------------------------------------")
    for idx, item in enumerate(unified, 1):
        v_str = f"v{item['version']}" if item["version"] != "Unknown" else "Unknown"
        lnch = os.path.basename(item["launcher"]) if item["launcher"] else "None"
        h_mode, k_mode = item["history_mode"], item["keyring_mode"]
        h_tag = f"{GREEN}{h_mode:<18}{NC}" if ("Shared" in h_mode or "Master" in h_mode) else (f"{YELLOW}{h_mode:<18}{NC}" if h_mode != "N/A" else f"{BLUE}{h_mode:<18}{NC}")
        k_tag = f"{GREEN}Normal{NC}" if "Normal" in k_mode else f"{BLUE}GNOME {NC}"
        print(f"  [{idx}] {item['name']:<35} {v_str:<9} in {item['engine_path']:<18} History: {h_tag} | Keyring: {k_tag} | {lnch}")
    print("----------------------------------------------------------------------------------------")
    print(f"{BOLD}Select an installation or clone [1-{len(unified)}] to EDIT its settings.{NC}\n")
    print(f"{BOLD}{CYAN}[ INSTANCES & PROFILES ]{NC}")
    print("  [C] Create Clone Profile     [L] Launch Instance          [H] Merge & Sync History")
    print("  [B] History Backups          [E] Export Archive           [I] Import Archive\n")
    print(f"{BOLD}{CYAN}[ INSTALLATION & UPDATES ]{NC}")
    print("  [N] Install New Binary       [U] Smart Update All         [W] Step-by-Step Wizard")
    print("  [S] Run Setup Step (1-8)     [V] Version & Status Table   [P] Update Repository")
    print("  [Z] Uninstall Apps & Data\n")
    print(f"{BOLD}{CYAN}[ PATCHES & CUSTOMIZATION ]{NC}")
    print("  [T] Multi-Account Selector   [J] Conversation Forking     [Y] Open in IDE Button")
    print("  [F] F5 Reload Patch          [R] RTL Typography Patch     [O] Icons & Visual Theme")
    print("  [CM] Custom Models UI Patch  [G] Keyring Storage Mode     [X] Clean Data & Cache\n")
    print(f"{BOLD}{CYAN}[ ACCOUNTS & SYSTEM ]{NC}")
    print("  [A] Multi-Account Manager    [M] Live Request Traffic     [K] Speed Benchmark")
    print("  [D] Restart Services         [Q] Exit Setup")
    print(f"{CYAN}========================================================================================{NC}")
