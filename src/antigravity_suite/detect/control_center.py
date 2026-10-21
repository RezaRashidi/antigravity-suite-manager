"""
Interactive Control Center terminal loop for Antigravity Suite Manager.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Dict, List

from antigravity_suite.detect.configure_unified import configure_unified_instance
from antigravity_suite.detect.constants import BLUE, BOLD, CYAN, GREEN, NC, REAL_HOME, RED, YELLOW
from antigravity_suite.detect.control_center_actions import (
    handle_control_center_backups,
    handle_control_center_clean_cache,
    handle_control_center_clone,
    handle_control_center_export_import,
    handle_control_center_f5_patch,
    handle_control_center_icons,
    handle_control_center_install,
    handle_control_center_keyring_global,
    handle_control_center_launch,
    handle_control_center_merge_history,
    handle_control_center_multi_account,
    handle_control_center_rtl_patch,
    handle_control_center_selector_patch,
    handle_control_center_status,
    handle_control_center_steps,
    handle_control_center_traffic,
    handle_control_center_update,
)
from antigravity_suite.detect.paths_config import save_paths_config
from antigravity_suite.detect.unified import get_unified_instances


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
    print("  [S] Run Setup Step (1-8)     [V] Version & Status Table   [P] Update Repository\n")
    print(f"{BOLD}{CYAN}[ PATCHES & CUSTOMIZATION ]{NC}")
    print("  [T] Multi-Account Selector   [F] F5 Reload Patch          [R] Apply RTL Patch")
    print("  [O] Icons & Visual Theme     [G] Keyring Storage Mode     [X] Clean Download Cache\n")
    print(f"{BOLD}{CYAN}[ ACCOUNTS & SYSTEM ]{NC}")
    print("  [A] Multi-Account Manager    [M] Live Request Traffic     [K] Speed Benchmark")
    print("  [D] Restart Services         [Q] Exit Setup")
    print(f"{CYAN}========================================================================================{NC}")


def run_control_center() -> None:
    local_bin = os.path.join(REAL_HOME, ".local", "bin")
    manage_sh = os.path.join(local_bin, "manage-antigravity.sh")
    if not os.path.isfile(manage_sh):
        manage_sh = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bin", "manage-antigravity.sh")
    installer_sh = os.path.join(os.path.dirname(manage_sh), "..", "install.sh")

    while True:
        unified, curr_app, curr_ide, custom_paths = get_unified_instances()
        render_control_center_overview(unified)
        try:
            choice = input(f"Select option [1-{len(unified)}, A-Z, Default: Q]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice in ["0", "", "q", "Q", "exit"]:
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(unified):
            curr_app, curr_ide = configure_unified_instance(unified[int(choice) - 1], curr_app, curr_ide, custom_paths)
            save_paths_config(curr_app, curr_ide, custom_paths)
        elif choice.upper() == "C":
            handle_control_center_clone(manage_sh)
        elif choice.upper() == "L":
            handle_control_center_launch(unified)
        elif choice.upper() == "H":
            handle_control_center_merge_history(manage_sh)
        elif choice.upper() == "B":
            handle_control_center_backups(local_bin)
        elif choice.upper() in ["E", "I"]:
            handle_control_center_export_import(choice, local_bin)
        elif choice.upper() == "N":
            handle_control_center_install(manage_sh)
        elif choice.upper() == "U":
            handle_control_center_update(manage_sh)
        elif choice.upper() == "W":
            sys.exit(10)
        elif choice.upper() == "S":
            handle_control_center_steps(manage_sh, installer_sh)
        elif choice.upper() == "V":
            handle_control_center_status(manage_sh)
        elif choice.upper() == "P":
            subprocess.run(["bash", manage_sh, "update-repo"], check=False)
            input("\nPress Enter to return to Control Center...")
        elif choice.upper() == "T":
            handle_control_center_selector_patch(manage_sh, unified)
        elif choice.upper() == "F":
            handle_control_center_f5_patch(manage_sh, unified)
        elif choice.upper() == "R":
            handle_control_center_rtl_patch(manage_sh, unified)
        elif choice.upper() == "O":
            handle_control_center_icons(manage_sh)
        elif choice.upper() == "G":
            handle_control_center_keyring_global(manage_sh)
        elif choice.upper() == "X":
            handle_control_center_clean_cache(manage_sh)
        elif choice.upper() == "A":
            handle_control_center_multi_account(manage_sh)
        elif choice.upper() == "M":
            handle_control_center_traffic(manage_sh)
        elif choice.upper() == "K":
            subprocess.run(["bash", manage_sh, "benchmark"], check=False)
            input("\nPress Enter to return to Control Center...")
        elif choice.upper() == "D":
            subprocess.run(["bash", manage_sh, "restart-services"], check=False)
            input("\nPress Enter to return to Control Center...")
        else:
            print(f"{RED}[ERROR] Unrecognized option '{choice}'.{NC}")
            input("\nPress Enter to continue...")
