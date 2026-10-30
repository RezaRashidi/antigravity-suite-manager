"""
Helper sub-dialogs for unified instance patches (Fork, Selector, Models, Open IDE).
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict

from antigravity_suite.detect.constants import CYAN, NC, YELLOW


def handle_unified_patch_fork(c_type: str, flag: str, u_item: Dict[str, Any], eng_p: str, manage_sh: str) -> None:
    inst_name = u_item.get("name", u_item.get("type", "Instance"))
    print(f"\n{CYAN}--- Conversation Forking Patch ({inst_name}) ---{NC}")
    print("  [1] Apply / Update Forking Patch\n  [2] Revert / Unpatch Forking Patch\n  [0] Cancel")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c in ["1", ""]:
        print(f"\n{CYAN}Applying Conversation Forking patch to {u_item['type']} at {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "fork", c_type, flag, eng_p, "--force"], check=False)
    elif c == "2":
        print(f"\n{CYAN}Reverting Conversation Forking patch from {u_item['type']} at {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "unpatch-fork", c_type, flag, eng_p], check=False)


def handle_unified_patch_selector(c_type: str, flag: str, u_item: Dict[str, Any], eng_p: str, manage_sh: str) -> None:
    inst_name = u_item.get("name", u_item.get("type", "Instance"))
    print(f"\n{CYAN}--- Multi-Account Selector Patch ({inst_name}) ---{NC}")
    print("  [1] Apply / Update Selector Patch\n  [2] Revert / Unpatch Selector Patch\n  [0] Cancel")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c in ["1", ""]:
        print(f"\n{CYAN}Applying Multi-Account Selector patch to {u_item['type']} at {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "selector", c_type, flag, eng_p, "--force"], check=False)
    elif c == "2":
        print(f"\n{CYAN}Reverting Multi-Account Selector patch from {u_item['type']} at {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "unpatch-selector", c_type, flag, eng_p], check=False)


def handle_unified_patch_models(u_item: Dict[str, Any], eng_p: str, manage_sh: str) -> None:
    if "IDE" in u_item.get("type", ""):
        print(f"\n{YELLOW}[NOTICE] Custom Models UI patch is for Antigravity Desktop App only.{NC}")
        return
    inst_name = u_item.get("name", u_item.get("type", "Instance"))
    print(f"\n{CYAN}--- In-App Custom Models Settings UI Patch ({inst_name}) ---{NC}")
    print("  [1] Apply / Inject Custom Models UI into App (Patch)\n  [2] Revert / Unpatch Custom Models UI")
    print("  [3] Open Custom Models CLI Manager (Providers, Keys, Discovery)\n  [0] Cancel")
    c = input("Select action [1-3, Default: 1]: ").strip()
    if c in ["1", ""]:
        print(f"\n{CYAN}Applying Custom Models UI patch to {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "patch-models", "--app-dir", eng_p, "--force"], check=False)
    elif c == "2":
        print(f"\n{CYAN}Reverting Custom Models UI patch from {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "unpatch-models", "--app-dir", eng_p], check=False)
    elif c == "3":
        subprocess.run(["bash", manage_sh, "custom-models", "menu"], check=False)


def handle_unified_patch_open_ide(u_item: Dict[str, Any], eng_p: str, manage_sh: str) -> None:
    if "IDE" in u_item.get("type", ""):
        print(f"\n{YELLOW}[NOTICE] 'Open in IDE' titlebar button is for Antigravity Desktop App only.{NC}")
        return
    inst_name = u_item.get("name", u_item.get("type", "Instance"))
    print(f"\n{CYAN}--- Native 'Open in IDE' Titlebar Button Patch ({inst_name}) ---{NC}")
    print("  [1] Enable Native 'Open in IDE' Titlebar Button in App\n  [2] Revert / Unpatch 'Open in IDE' Button\n  [0] Cancel")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c in ["1", ""]:
        print(f"\n{CYAN}Applying 'Open in IDE' patch to {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "open-ide", "--app-dir", eng_p, "--force"], check=False)
    elif c == "2":
        print(f"\n{CYAN}Reverting 'Open in IDE' patch from {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "unpatch-open-ide", "--app-dir", eng_p], check=False)
