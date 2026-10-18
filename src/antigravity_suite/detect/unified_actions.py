"""
Engine and installation action handlers for unified instances.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Tuple

from antigravity_suite.detect.constants import CYAN, GREEN, NC
from antigravity_suite.detect.launchers import get_launcher_binary, update_launcher_binary
from antigravity_suite.detect.paths_config import save_paths_config


def handle_unified_engine_relocate(eng_p: str, is_p_app: bool, is_p_ide: bool, curr_app: str, curr_ide: str, custom_paths: List[str], launcher_f: str, u_item: Dict[str, Any]) -> Tuple[str, str, str]:
    old_p = eng_p
    new_p = input(f"\nEnter new installation directory path [current: {old_p}]: ").strip()
    if new_p and new_p != old_p:
        new_p = os.path.realpath(os.path.expanduser(new_p))
        if not os.path.isdir(new_p): os.makedirs(new_p, exist_ok=True)
        if input(f"Copy existing installation files from {old_p} to {new_p}? [Y/n]: ").strip().lower() not in ["n", "no"]:
            subprocess.run(["cp", "-a", f"{old_p}/.", f"{new_p}/"], check=False)
        if is_p_app: curr_app = new_p
        if is_p_ide: curr_ide = new_p
        if old_p in custom_paths: custom_paths.remove(old_p)
        if new_p not in custom_paths and new_p not in [curr_app, curr_ide]: custom_paths.append(new_p)
        u_item["engine_path"] = new_p
        eng_p = new_p
        if launcher_f and os.path.isfile(launcher_f):
            old_bin = get_launcher_binary(launcher_f)
            if old_bin.startswith(old_p):
                update_launcher_binary(launcher_f, old_bin.replace(old_p, new_p, 1))
        save_paths_config(curr_app, curr_ide, custom_paths)
        print(f"{GREEN}[SUCCESS] Engine directory relocated to: {new_p}{NC}")
    return eng_p, curr_app, curr_ide


def handle_unified_target_role(eng_p: str, is_p_app: bool, is_p_ide: bool, curr_app: str, curr_ide: str) -> Tuple[str, str]:
    print("\nSelect Suite Role:\n  [1] Set as Primary App Target\n  [2] Set as Primary IDE Target\n  [3] Clear Primary Target role")
    r_ans = input("Choose role [1-3]: ").strip()
    if r_ans == "1":
        curr_app = eng_p
        print(f"{GREEN}[SUCCESS] Set {eng_p} as Primary App Target.{NC}")
    elif r_ans == "2":
        curr_ide = eng_p
        print(f"{GREEN}[SUCCESS] Set {eng_p} as Primary IDE Target.{NC}")
    elif r_ans == "3":
        if is_p_app: curr_app = ""
        if is_p_ide: curr_ide = ""
        print(f"{GREEN}[SUCCESS] Cleared primary role for {eng_p}.{NC}")
    return curr_app, curr_ide


def handle_unified_patches_and_reinstall(choice: str, u_item: Dict[str, Any], eng_p: str, manage_sh: str) -> None:
    c_type = "ide" if "IDE" in u_item.get("type", "") else "app"
    flag = "--ide-dir" if c_type == "ide" else "--app-dir"
    if choice in ["8", "5"]:
        print(f"\n{CYAN}Downloading & installing fresh {u_item['type']} into {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "install", c_type, flag, eng_p], check=False)
    elif choice.upper() == "R":
        print(f"\n{CYAN}Applying RTL patch to {u_item['type']} at {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "rtl", c_type, flag, eng_p], check=False)
    elif choice.upper() == "F" and "IDE" not in u_item.get("type", ""):
        print(f"\n{CYAN}Applying F5 reload & isolation patch to {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "f5", "--app-dir", eng_p], check=False)
