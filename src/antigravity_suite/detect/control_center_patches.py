"""
Patch management actions for Control Center (Selector, Fork, F5, RTL, Open IDE).
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict, List, Optional
from antigravity_suite.detect.constants import BOLD, CYAN, NC, RED
from antigravity_suite.detect.control_center_patches_helpers import run_target_patch


def handle_control_center_selector_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- Prompt-Bar Multi-Account Selector Patch ---{NC}")
    print("  [1] Apply / Update Prompt-Bar Multi-Account Selector Patch\n  [2] Revert / Unpatch Prompt-Bar Selector Patch (Preserves F5)\n  [0] Return")
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


def handle_control_center_f5_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- F5 Manual Sync Backend Reload Patch ---{NC}")
    print("  [1] Apply / Re-apply F5 Backend Reload Patch\n  [2] Revert / Unpatch F5 Reload Patch\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c in ["0"]: return
    action_cmd = "unpatch-f5" if c == "2" else "f5"
    app_instances = [it for it in (unified or []) if "IDE" not in it.get("type", "")]
    if app_instances:
        print(f"\n{BOLD}Target App Instance for F5 Patch:{NC}\n  [A] All App Instances")
        for idx, item in enumerate(app_instances, 1):
            print(f"  [{idx}] {item['name']} at {item['engine_path']}")
        print("  [0] Cancel")
        t = input(f"Select target [A, 1-{len(app_instances)}, Default: A]: ").strip()
        if t in ["0"]: return
        if t.upper() in ["A", ""]:
            for it in app_instances:
                subprocess.run(["bash", manage_sh, action_cmd, "--app-dir", it["engine_path"], "--force"], check=False)
        elif t.isdigit() and 1 <= int(t) <= len(app_instances):
            subprocess.run(["bash", manage_sh, action_cmd, "--app-dir", app_instances[int(t) - 1]["engine_path"], "--force"], check=False)
        else: print(f"{RED}[ERROR] Invalid target selection.{NC}")
    else:
        subprocess.run(["bash", manage_sh, action_cmd, "--force"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_rtl_patch(manage_sh: str, unified: Optional[List[Dict[str, Any]]] = None) -> None:
    print(f"\n{CYAN}--- RTL Layout & Font Patch (mmnaderi/antigravity-rtl) ---{NC}")
    print("  [1] Apply / Update RTL Patch (App & IDE)\n  [2] Revert / Unpatch RTL Patch\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c not in ["0"]:
        run_target_patch(manage_sh, "unpatch-rtl" if c == "2" else "rtl", unified, "RTL Patch", force=(c != "2"))
