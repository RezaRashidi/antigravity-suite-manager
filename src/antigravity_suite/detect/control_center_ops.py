"""
Operational actions for Control Center (Status, Icons, Keyring, Traffic, Accounts).
"""

from __future__ import annotations

import subprocess
from antigravity_suite.detect.constants import CYAN, NC


def handle_control_center_multi_account(manage_sh: str) -> None:
    subprocess.run(["bash", manage_sh, "multi-account"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_traffic(manage_sh: str) -> None:
    subprocess.run(["bash", manage_sh, "trace"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_merge_history(manage_sh: str) -> None:
    subprocess.run(["bash", manage_sh, "merge-history"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_icons(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Icons & Appearance Configuration ---{NC}\n  [1] Interactive Configuration  [2] Re-apply Theme  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c in ["1", ""]: subprocess.run(["bash", manage_sh, "set-icons"], check=False)
    elif c == "2": subprocess.run(["bash", manage_sh, "set-icons", "apply"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_status(manage_sh: str) -> None:
    subprocess.run(["bash", manage_sh, "status"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_keyring_global(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Keyring Storage Management ---{NC}\n  [1] Status  [2] Normal File Storage  [3] GNOME Keyring  [4] Purge Credentials  [0] Return")
    c = input("Select action [1-4, Default: 1]: ").strip()
    k_map = {"1": ["keyring", "status"], "2": ["keyring", "set", "all", "normal"], "3": ["keyring", "set", "all", "gnome"], "4": ["keyring", "purge"]}
    if c in k_map: subprocess.run(["bash", manage_sh] + k_map[c], check=False)
    elif c in [""]: subprocess.run(["bash", manage_sh, "keyring", "status"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_clean_cache(manage_sh: str) -> None:
    subprocess.run(["bash", manage_sh, "clean-cache"], check=False)
    input("\nPress Enter to return to Control Center...")
