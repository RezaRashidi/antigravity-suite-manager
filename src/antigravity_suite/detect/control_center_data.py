"""
Backup and Data Cleanup actions for Control Center.
"""

from __future__ import annotations

import os
import subprocess
import sys
from antigravity_suite.detect.constants import CYAN, NC, RED, get_bin_script


def handle_control_center_export_import(choice: str, local_bin: str) -> None:
    tool_py = get_bin_script("antigravity-migration.py")
    if choice.upper() == "E":
        print(f"\n{CYAN}--- Export Antigravity Suite or History Archive ---{NC}\n  [1] Full Bundle  [2] History Only  [3] Suite Configs Only")
        exp_c = input("Enter selection [1-3, Default: 1]: ").strip()
        dest = input("Enter output tarball path [Enter for default]: ").strip()
        cmd = [sys.executable, tool_py, "export-history" if exp_c == "2" else ("export-suite" if exp_c == "3" else "export-all")]
        if dest: cmd.append(os.path.realpath(os.path.expanduser(dest)))
        subprocess.run(cmd, check=False)
    else:
        arc = input("Enter path to archive (.tar.gz) to import: ").strip()
        if arc and os.path.isfile(os.path.realpath(os.path.expanduser(arc))):
            subprocess.run([sys.executable, tool_py, "import-all", os.path.realpath(os.path.expanduser(arc))], check=False)
        else: print(f"{RED}[ERROR] File not found or not specified.{NC}")
    input("\nPress Enter to return to Control Center...")


def handle_control_center_backups(local_bin: str) -> None:
    print(f"\n{CYAN}--- Manage Antigravity Backups & Snapshots ---{NC}\n  [1] List Snapshots  [2] Full Suite Backup  [3] App Backup  [4] IDE Backup  [5] History Backup  [6] Restore  [0] Return")
    b_c = input("Enter choice [0-6, Default: 1]: ").strip()
    tool_py = get_bin_script("antigravity-migration.py")
    cat_map = {"2": "all", "3": "app", "4": "ide", "5": "history"}
    if b_c in cat_map:
        subprocess.run([sys.executable, tool_py, "create-backup", "--category", cat_map[b_c], "--label", f"{cat_map[b_c]}_control_center"], check=False)
    elif b_c == "6":
        tar_in = input("Enter path to backup archive to restore: ").strip()
        if tar_in and os.path.isfile(os.path.realpath(os.path.expanduser(tar_in))):
            subprocess.run([sys.executable, tool_py, "restore-backup", os.path.realpath(os.path.expanduser(tar_in))], check=False)
        else: print(f"{RED}[ERROR] Invalid backup path.{NC}")
    elif b_c != "0":
        subprocess.run([sys.executable, tool_py, "list-backups"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_clean_data(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Clean / Delete Antigravity Data & Cache ---{NC}\n  [1] App Data  [2] IDE Data  [3] Shared History  [4] ALL Data (Clean Slate)  [5] Cache (/tmp)  [0] Return")
    c = input("Select action [0-5, Default: 0]: ").strip()
    acts = {"1": ("clean-data", "app"), "2": ("clean-data", "ide"), "3": ("clean-data", "history"), "4": ("clean-data", "all"), "5": ("clean-cache", "")}
    if c in acts:
        cmd = ["bash", manage_sh, acts[c][0]] + ([acts[c][1]] if acts[c][1] else [])
        subprocess.run(cmd, check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_uninstall(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Uninstall Antigravity Suite ---{NC}\n  [1] App (Keep Data)  [2] App (Purge Data)  [3] IDE (Keep Data)  [4] IDE (Purge Data)  [5] Both (Keep Data)  [6] Everything (Purge All)  [0] Return")
    u_c = input("Select action [0-6, Default: 0]: ").strip()
    u_map = {"1": ("app", "--keep-data"), "2": ("app", "--with-data"), "3": ("ide", "--keep-data"), "4": ("ide", "--with-data"), "5": ("all", "--keep-data"), "6": ("all", "--with-data")}
    if u_c in u_map:
        subprocess.run(["bash", manage_sh, "uninstall", u_map[u_c][0], u_map[u_c][1]], check=False)
    input("\nPress Enter to return to Control Center...")
