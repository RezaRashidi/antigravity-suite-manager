"""
Specific action handlers for configuring single clones and profiles.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from typing import Any, Dict

from antigravity_suite.detect.constants import CYAN, GREEN, NC, RED, YELLOW
from antigravity_suite.detect.launchers import get_launcher_binary, update_launcher_binary, update_launcher_profile_path
from antigravity_suite.detect.scan import scan_installations


def handle_clone_binary_change(launcher_f: str) -> None:
    if not os.path.isfile(launcher_f):
        print(f"{RED}[ERROR] Launcher script {launcher_f} does not exist.{NC}")
        return
    installs = scan_installations()
    print("\nSelect engine binary to link to this clone:")
    valid_bins = [(i["type"], i["version"], i["executable"]) for i in installs if i.get("executable") and os.path.isfile(i["executable"])]
    for idx, (t, v, exe) in enumerate(valid_bins, 1):
        print(f"  [{idx}] {t} ({v}) -> {exe}")
    print("  [C] Enter custom binary executable path")
    b_ans = input(f"Select choice [1-{len(valid_bins)}, C]: ").strip()
    new_exe = ""
    if b_ans.isdigit() and 1 <= int(b_ans) <= len(valid_bins):
        new_exe = valid_bins[int(b_ans) - 1][2]
    elif b_ans.upper() == "C":
        c_exe = os.path.realpath(os.path.expanduser(input("Enter full path to executable: ").strip()))
        if os.path.isfile(c_exe): new_exe = c_exe
    if new_exe:
        if update_launcher_binary(launcher_f, new_exe):
            print(f"{GREEN}[SUCCESS] Updated launcher {launcher_f} to execute: {new_exe}{NC}")
        else:
            print(f"{RED}[ERROR] Failed to update launcher file.{NC}")


def handle_clone_profile_relocate(clone: Dict[str, Any], launcher_f: str, p_dir: str, is_acc1: bool, is_acc2: bool) -> None:
    if is_acc1:
        print(f"{YELLOW}[NOTICE] Primary Antigravity profile (~/.gemini) cannot be relocated.{NC}")
        return
    if is_acc2:
        print(f"{YELLOW}[NOTICE] Standard Account 2 profile (~/.antigravity-profile2) cannot be relocated.{NC}")
        return
    new_p = input(f"Enter new path for profile directory [current: {p_dir}]: ").strip()
    if new_p and new_p != p_dir:
        new_p = os.path.realpath(os.path.expanduser(new_p))
        os.makedirs(os.path.dirname(new_p), exist_ok=True)
        shutil.move(p_dir, new_p)
        if os.path.isfile(launcher_f):
            update_launcher_profile_path(launcher_f, is_acc2, p_dir, new_p)
        clone["profile_dir"] = new_p
        print(f"{GREEN}[SUCCESS] Profile directory moved to {new_p} and launcher updated.{NC}")


def handle_clone_create_or_delete(clone: Dict[str, Any], launcher_f: str, p_dir: str, is_ide1: bool, is_acc1: bool, is_acc2: bool, cid: str, manage_sh: str, local_apps: str) -> bool:
    if is_ide1:
        print(f"\n{CYAN}--- Create Additional IDE Clone / Profile ---{NC}")
        if os.path.isfile(manage_sh): subprocess.run(["bash", manage_sh, "create-instance", "ide"], check=False)
        return True
    elif is_acc1:
        print(f"\n{CYAN}--- Create Additional App Account Profile ---{NC}\n  [1] Standard Account 2\n  [2] Custom App Profile")
        if input("Choose option [1-2, Default: 1]: ").strip() == "2":
            subprocess.run(["bash", manage_sh, "create-instance", "app"], check=False)
        else:
            subprocess.run(["bash", manage_sh, "app2"], check=False)
        subprocess.run(["bash", manage_sh, "app1"], check=False)
        return True
    else:
        if input(f"Are you sure you want to delete clone '{clone['name']}'? [y/N]: ").strip().lower() in ["y", "yes"]:
            if os.path.isfile(launcher_f):
                try: os.remove(launcher_f)
                except Exception: pass
            if os.path.isfile(clone["desktop"]):
                try: os.remove(clone["desktop"])
                except Exception: pass
            if input(f"Also delete profile directory '{p_dir}' and settings? [y/N]: ").strip().lower() in ["y", "yes"]:
                shutil.rmtree(p_dir, ignore_errors=True)
            subprocess.run(["update-desktop-database", local_apps], check=False, stderr=subprocess.DEVNULL)
            if is_acc2 or "app-" in cid: subprocess.run(["bash", manage_sh, "app1"], check=False)
            print(f"{GREEN}[SUCCESS] Clone '{clone['name']}' removed.{NC}")
            return True
    return False
