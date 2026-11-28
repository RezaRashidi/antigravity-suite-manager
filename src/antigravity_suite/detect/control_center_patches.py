"""
Patch management actions for Control Center (Selector, Fork, RTL, Open IDE).
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict, List, Optional
from antigravity_suite.detect.constants import BOLD, CYAN, NC, RED
from antigravity_suite.detect.control_center_patches_helpers import run_target_patch


def handle_control_center_selector_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- Prompt-Bar Multi-Account Selector Patch ---{NC}")
    print("  [1] Apply / Update Prompt-Bar Multi-Account Selector Patch\n  [2] Revert / Unpatch Prompt-Bar Selector Patch\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c not in ["0"]:
        run_target_patch(manage_sh, "unpatch-selector" if c == "2" else "selector", unified, "Selector Patch", force=True)


def handle_control_center_experiments_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- Unified Experiments, Forking, Cost & Open-IDE Patch (App & IDE) ---{NC}")
    print("  [1] Apply / Update Flags, Forking, Cost & Open-IDE Patch\n  [2] Revert / Unpatch Unified Experiments Patch\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c not in ["0"]:
        run_target_patch(manage_sh, "unpatch-experiments" if c == "2" else "experiments", unified, "Unified Experiments Patch", force=True)


def handle_control_center_fork_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    handle_control_center_experiments_patch(manage_sh, unified)


def handle_control_center_open_ide_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    handle_control_center_experiments_patch(manage_sh, unified)


def handle_control_center_window_bounds_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- X11 Window Bounds Fix Patch (App v2.30+) ---{NC}")
    print("  [1] Apply / Update X11 Window Bounds Fix in App\n  [2] Revert / Unpatch X11 Window Bounds Fix\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c not in ["0"]:
        run_target_patch(manage_sh, "unpatch-window" if c == "2" else "patch-window", unified, "Window Bounds Patch", force=True)



def handle_control_center_rtl_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- RTL Layout & Font Patch (Suite Internal) ---{NC}")
    print("  [1] Apply / Update RTL Patch (App & IDE)\n  [2] Revert / Unpatch RTL Patch\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c not in ["0"]:
        run_target_patch(manage_sh, "unpatch-rtl" if c == "2" else "rtl", unified, "RTL Patch", force=(c != "2"))


def handle_control_center_models_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- In-App Custom Models Settings UI Patch ---{NC}")
    print("  [1] Apply / Inject Custom Models UI into Antigravity App (Patch)")
    print("  [2] Revert / Unpatch Custom Models UI from Antigravity App")
    print("  [3] Open Custom Models CLI Manager (Providers, Keys, Discovery)")
    print("  [0] Return")
    c = input("Select action [1-3, Default: 1]: ").strip()
    if c in ["0"]:
        return
    if c == "2":
        subprocess.run(["bash", manage_sh, "unpatch-models"], check=False)
    elif c == "3":
        subprocess.run(["bash", manage_sh, "custom-models", "menu"], check=False)
    else:
        subprocess.run(["bash", manage_sh, "patch-models", "--force"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_patch_all(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- Apply All Antigravity Patches (Models, RTL, Selector, Experiments/Fork/IDE, WB) ---{NC}")
    print("  [1] Apply All Patches (App & IDE in dependency order)")
    print("  [2] Revert / Restore All Patches (Clean pristine state)")
    print("  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c in ["0"]:
        return
    if c == "2":
        subprocess.run(["bash", manage_sh, "unpatch"], check=False)
    else:
        run_target_patch(manage_sh, "patch-all", unified, "All Patches", force=True)

