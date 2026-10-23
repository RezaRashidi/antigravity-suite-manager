"""
Installation, Cloning, and Launching actions for Control Center.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List
from antigravity_suite.detect.constants import CYAN, GREEN, NC, RED, YELLOW


def handle_control_center_install(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Install New Google Antigravity Binary ---{NC}\n  [1] Antigravity App  [2] Antigravity IDE  [3] Both")
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
    print(f"\n{CYAN}--- Create New Clone / Account Profile ---{NC}\n  [1] App Profile  [2] IDE Profile")
    target_itype = "ide" if input("Enter choice [1-2, Default: 1]: ").strip() == "2" else "app"
    subprocess.run(["bash", manage_sh, "create-instance", target_itype], check=False)
    subprocess.run(["bash", manage_sh, "app1"], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_launch(unified: List[Dict[str, Any]]) -> None:
    print(f"\n{CYAN}--- Launch Antigravity Suite Instance ---{NC}")
    launchables = [(idx, it["name"], it["launcher"]) for idx, it in enumerate(unified, 1) if it.get("launcher") and os.path.isfile(it["launcher"])]
    if not launchables:
        print(f"{YELLOW}[WARN] No valid launcher binaries detected.{NC}")
        input("\nPress Enter to return to Control Center...")
        return
    for idx, name, lnch in launchables:
        print(f"  [{idx}] {name} ({os.path.basename(lnch)})")
    choice = input(f"Select instance [1-{len(unified)}, 0 to cancel]: ").strip()
    target = next((item for item in launchables if str(item[0]) == choice), None)
    if target:
        try:
            subprocess.Popen([target[2]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            print(f"{GREEN}[SUCCESS] Launched {target[1]} in background.{NC}")
        except Exception as e: print(f"{RED}[ERROR] Failed to launch: {e}{NC}")
    elif choice and choice != "0": print(f"{RED}[ERROR] Invalid selection '{choice}'.{NC}")
    input("\nPress Enter to return to Control Center...")


def handle_control_center_steps(manage_sh: str, installer_sh: str) -> None:
    print(f"\n{CYAN}=== Select Setup Step (1-8, U: Update, 0: Return) ==={NC}")
    s_choice = input("Select option [1-8, U, 0 to cancel]: ").strip()
    if s_choice.upper() == "U": subprocess.run(["bash", manage_sh, "update"], check=False)
    elif s_choice.isdigit() and 1 <= int(s_choice) <= 8:
        subprocess.run(["bash", manage_sh, "--only-step", s_choice], check=False)
    input("\nPress Enter to return to Control Center...")


def handle_control_center_update(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Smart Update Antigravity Suite ---{NC}\n  [1] Everything  [2] App  [3] IDE  [4] RTL  [5] F5  [0] Return")
    u_c = input("Select update target [1-5, Default: 1]: ").strip()
    acts = {"2": ["update", "app"], "3": ["update", "ide"], "4": ["update-rtl"], "5": ["update-f5"]}
    subprocess.run(["bash", manage_sh] + acts.get(u_c, ["update"]), check=False)
    input("\nPress Enter to return to Control Center...")
