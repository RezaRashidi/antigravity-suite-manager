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


def handle_control_center_fork_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- Experimental Conversation Forking Patch ---{NC}")
    print("  [1] Apply / Update Conversation Forking Patch (App & IDE)\n  [2] Revert / Unpatch Conversation Forking Patch\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c not in ["0"]:
        run_target_patch(manage_sh, "unpatch-fork" if c == "2" else "fork", unified, "Fork Patch", force=True)


def handle_control_center_open_ide_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- Native 'Open in IDE' Titlebar Button Patch ---{NC}")
    print("  [1] Enable Native 'Open in IDE' Titlebar Button in App\n  [2] Revert / Unpatch 'Open in IDE' Button\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c not in ["0"]:
        run_target_patch(manage_sh, "unpatch-open-ide" if c == "2" else "open-ide", unified, "Open IDE Patch", force=True)


def handle_control_center_window_bounds_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- X11 Window Bounds Fix Patch (App v2.30+) ---{NC}")
    print("  [1] Apply / Update X11 Window Bounds Fix in App\n  [2] Revert / Unpatch X11 Window Bounds Fix\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c not in ["0"]:
        run_target_patch(manage_sh, "unpatch-window" if c == "2" else "patch-window", unified, "Window Bounds Patch", force=True)


def handle_control_center_typing_perf_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- Prompt Input Typing Performance Patch (App & IDE) ---{NC}")
    print("  [1] Apply / Update Prompt Input Typing Performance Patch (App & IDE)\n  [2] Revert / Unpatch Typing Performance Patch\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c not in ["0"]:
        run_target_patch(manage_sh, "unpatch-typing" if c == "2" else "patch-typing", unified, "Typing Performance Patch", force=True)


def handle_control_center_rtl_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- RTL Layout & Font Patch (mmnaderi/antigravity-rtl) ---{NC}")
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
    print(f"\n{CYAN}--- Apply All Antigravity Patches (Models, RTL, Selector, Fork, Open IDE) ---{NC}")
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

