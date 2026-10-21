"""
Sub-action handlers for the Antigravity Suite Control Center.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Dict, List

from antigravity_suite.detect.constants import BOLD, CYAN, GREEN, NC, RED, YELLOW


def handle_control_center_install(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Install New Google Antigravity Binary ---{NC}\n  [1] Antigravity App\n  [2] Antigravity IDE\n  [3] Both App & IDE")
    comp = input("Choose component [1-3, Default: 1]: ").strip()
    target_comp = "app" if comp == "1" else ("ide" if comp == "2" else "all")
    dest = input("Enter destination directory [Enter for default]: ").strip()
    cmd = ["bash", manage_sh, "install", target_comp]
    if dest:
        flag = "--app-dir" if target_comp in ["app", "all"] else "--ide-dir"
        cmd.extend([flag, os.path.realpath(os.path.expanduser(dest))])
    subprocess.run(cmd, check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_clone(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Create New Clone / Account Profile ---{NC}\n  [1] Antigravity App Profile\n  [2] Antigravity IDE Profile")
    target_itype = "ide" if input("Enter choice [1-2, Default: 1]: ").strip() == "2" else "app"
    subprocess.run(["bash", manage_sh, "create-instance", target_itype], check=False)
    subprocess.run(["bash", manage_sh, "app1"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_launch(unified: List[Dict[str, Any]]) -> None:
    print(f"\n{CYAN}--- Launch Antigravity Suite Instance ---{NC}")
    launchables = []
    for idx, item in enumerate(unified, 1):
        lnch = item.get("launcher")
        if lnch and os.path.isfile(lnch):
            launchables.append((idx, item["name"], lnch))
            print(f"  [{idx}] {item['name']} ({os.path.basename(lnch)})")

    if not launchables:
        print(f"{YELLOW}[WARN] No valid launcher binaries detected.{NC}")
        input("\nPress Enter to return to Control Center...")
        return

    choice = input(f"Select instance to launch [1-{len(unified)}, 0 to cancel]: ").strip()
    if not choice or choice == "0":
        return

    target = next((item for item in launchables if str(item[0]) == choice), None)
    if target:
        idx, name, bin_path = target
        try:
            subprocess.Popen([bin_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            print(f"{GREEN}[SUCCESS] Launched {name} ({os.path.basename(bin_path)}) in background.{NC}")
        except Exception as e:
            print(f"{RED}[ERROR] Failed to launch {name}: {e}{NC}")
    else:
        print(f"{RED}[ERROR] Invalid selection '{choice}'.{NC}")
    input("\nPress Enter to return to Control Center...")


def handle_control_center_export_import(choice: str, local_bin: str) -> None:
    tool_py = os.path.join(local_bin, "antigravity-migration.py")
    if not os.path.isfile(tool_py):
        tool_py = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bin", "antigravity-migration.py")
    if choice.upper() == "E":
        print(f"\n{CYAN}--- Export Antigravity Suite or History Archive ---{NC}\n  [1] Full Bundle\n  [2] History Only\n  [3] Suite Configs Only")
        exp_c = input("Enter selection [1-3, Default: 1]: ").strip()
        dest_in = input("Enter output tarball path [Enter for default]: ").strip()
        cmd = [sys.executable, tool_py, "export-history" if exp_c == "2" else ("export-suite" if exp_c == "3" else "export-all")]
        if dest_in: cmd.append(os.path.realpath(os.path.expanduser(dest_in)))
        subprocess.run(cmd, check=False)
    else:
        print(f"\n{CYAN}--- Import Antigravity Suite or History Archive ---{NC}")
        arc = input("Enter path to archive (.tar.gz) to import: ").strip()
        if not arc or not os.path.isfile(os.path.realpath(os.path.expanduser(arc))):
            print(f"{RED}[ERROR] File not found or not specified.{NC}")
        else:
            subprocess.run([sys.executable, tool_py, "import-all", os.path.realpath(os.path.expanduser(arc))], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_backups(local_bin: str) -> None:
    print(f"\n{CYAN}--- Manage Antigravity History & Suite Backups ---{NC}\n  [1] List Available Safety Snapshots\n  [2] Create New Snapshot\n  [3] Restore System")
    b_c = input("Enter choice [1-3, Default: 1]: ").strip()
    tool_py = os.path.join(local_bin, "antigravity-migration.py")
    if not os.path.isfile(tool_py):
        tool_py = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bin", "antigravity-migration.py")
    if b_c == "2":
        subprocess.run([sys.executable, tool_py, "create-backup", "--category", "all", "--label", "manual_control_center"], check=False)
    elif b_c == "3":
        tar_in = input("Enter path to backup archive to restore: ").strip()
        if tar_in and os.path.isfile(os.path.realpath(os.path.expanduser(tar_in))):
            subprocess.run([sys.executable, tool_py, "restore-backup", os.path.realpath(os.path.expanduser(tar_in))], check=False)
        else: print(f"{RED}[ERROR] Invalid backup path.{NC}")
    else:
        subprocess.run([sys.executable, tool_py, "list-backups"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_steps(manage_sh: str, installer_sh: str) -> None:
    print(f"\n{CYAN}=== Select Setup Step (1: Deps, 2: Paths, 3: Resampler, 4: Tools, 5: Icons, 6: Keyring, 7: Download, 8: Launchers, U: Update, 0: Return) ==={NC}")
    s_choice = input("Select option [1-8, U, 0 to cancel]: ").strip()
    if s_choice.upper() == "U":
        subprocess.run(["bash", manage_sh, "update"], check=False)
    elif s_choice.isdigit() and 1 <= int(s_choice) <= 8:
        cmd = ["bash", manage_sh, "--only-step", s_choice]
        subprocess.run(cmd, check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_update(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Smart Update Antigravity Suite ---{NC}")
    print("  [1] Update Everything (App, IDE, RTL, F5, Checksums)\n  [2] Update Antigravity App Only\n  [3] Update Antigravity IDE Only\n  [4] Update RTL Patch Package\n  [5] Re-apply F5 Reload Patch\n  [0] Return")
    u_c = input("Select update target [1-5, Default: 1]: ").strip()
    if u_c == "2": subprocess.run(["bash", manage_sh, "update", "app"], check=False)
    elif u_c == "3": subprocess.run(["bash", manage_sh, "update", "ide"], check=False)
    elif u_c == "4": subprocess.run(["bash", manage_sh, "update-rtl"], check=False)
    elif u_c == "5": subprocess.run(["bash", manage_sh, "update-f5"], check=False)
    elif u_c in ["1", ""]: subprocess.run(["bash", manage_sh, "update"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_multi_account(manage_sh: str) -> None:
    subprocess.run(["bash", manage_sh, "multi-account"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_traffic(manage_sh: str) -> None:
    subprocess.run(["bash", manage_sh, "trace"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_selector_patch(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Prompt-Bar Multi-Account Selector Patch ---{NC}")
    print("  [1] Apply / Update Prompt-Bar Multi-Account Selector Patch\n  [2] Revert / Unpatch Prompt-Bar Selector Patch (Preserves F5)\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c in ["1", ""]:
        subprocess.run(["bash", manage_sh, "selector"], check=False)
    elif c == "2":
        subprocess.run(["bash", manage_sh, "unpatch-selector"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_f5_patch(manage_sh: str) -> None:
    print(f"\n{CYAN}--- F5 Manual Sync Backend Reload Patch ---{NC}")
    print("  [1] Apply / Re-apply F5 Backend Reload Patch\n  [2] Revert / Unpatch F5 Reload Patch\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c in ["1", ""]:
        subprocess.run(["bash", manage_sh, "f5"], check=False)
    elif c == "2":
        subprocess.run(["bash", manage_sh, "unpatch-f5"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_merge_history(manage_sh: str) -> None:
    subprocess.run(["bash", manage_sh, "merge-history"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_icons(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Icons & Appearance Configuration ---{NC}")
    print("  [1] Interactive Icon Theme Configuration\n  [2] Re-apply Current Icon Theme & Resample Icons\n  [0] Return")
    c = input("Select action [1-2, Default: 1]: ").strip()
    if c in ["1", ""]:
        subprocess.run(["bash", manage_sh, "set-icons"], check=False)
    elif c == "2":
        subprocess.run(["bash", manage_sh, "set-icons", "apply"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_status(manage_sh: str) -> None:
    subprocess.run(["bash", manage_sh, "status"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_keyring_global(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Credential Keyring Storage Management ---{NC}")
    print("  [1] Show Keyring Storage Status for All Instances\n  [2] Set All Instances to Normal File Storage (Decoupled from GNOME Keyring)\n  [3] Set All Instances to GNOME Keyring\n  [4] Purge / Clean Stale Keyring Credentials\n  [0] Return")
    c = input("Select action [1-4, Default: 1]: ").strip()
    if c in ["1", ""]:
        subprocess.run(["bash", manage_sh, "keyring", "status"], check=False)
    elif c == "2":
        subprocess.run(["bash", manage_sh, "keyring", "set", "all", "normal"], check=False)
    elif c == "3":
        subprocess.run(["bash", manage_sh, "keyring", "set", "all", "gnome"], check=False)
    elif c == "4":
        subprocess.run(["bash", manage_sh, "keyring", "purge"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_clean_cache(manage_sh: str) -> None:
    subprocess.run(["bash", manage_sh, "clean-cache"], check=False)
    input("\nPress Enter to return to Control Center...")
