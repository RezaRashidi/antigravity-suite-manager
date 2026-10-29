"""
Action dispatch routing for Control Center.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict, List

from antigravity_suite.detect.constants import NC, RED
from antigravity_suite.detect.control_center_actions import (
    handle_control_center_backups,
    handle_control_center_clean_data,
    handle_control_center_clone,
    handle_control_center_export_import,
    handle_control_center_f5_patch,
    handle_control_center_fork_patch,
    handle_control_center_icons,
    handle_control_center_install,
    handle_control_center_keyring_global,
    handle_control_center_launch,
    handle_control_center_merge_history,
    handle_control_center_models_patch,
    handle_control_center_multi_account,
    handle_control_center_open_ide_patch,
    handle_control_center_rtl_patch,
    handle_control_center_selector_patch,
    handle_control_center_status,
    handle_control_center_steps,
    handle_control_center_traffic,
    handle_control_center_uninstall,
    handle_control_center_update,
)


def dispatch_control_center_choice(choice: str, manage_sh: str, installer_sh: str, local_bin: str, unified: List[Dict[str, Any]]) -> None:
    up = choice.upper()
    if up == "C": handle_control_center_clone(manage_sh)
    elif up == "L": handle_control_center_launch(unified)
    elif up == "H": handle_control_center_merge_history(manage_sh)
    elif up == "B": handle_control_center_backups(local_bin)
    elif up in ["E", "I"]: handle_control_center_export_import(choice, local_bin)
    elif up == "N": handle_control_center_install(manage_sh)
    elif up == "U": handle_control_center_update(manage_sh)
    elif up == "W": sys.exit(10)
    elif up == "S": handle_control_center_steps(manage_sh, installer_sh)
    elif up == "V": handle_control_center_status(manage_sh)
    elif up == "P":
        subprocess.run(["bash", manage_sh, "update-repo"], check=False)
        input("\nPress Enter to return to Control Center...")
    elif up == "T": handle_control_center_selector_patch(manage_sh, unified)
    elif up == "J": handle_control_center_fork_patch(manage_sh, unified)
    elif up == "Y": handle_control_center_open_ide_patch(manage_sh, unified)
    elif up == "F": handle_control_center_f5_patch(manage_sh, unified)
    elif up == "R": handle_control_center_rtl_patch(manage_sh, unified)
    elif up in ["CM", "MODELS"]: handle_control_center_models_patch(manage_sh, unified)
    elif up == "O": handle_control_center_icons(manage_sh)
    elif up == "G": handle_control_center_keyring_global(manage_sh)
    elif up == "X": handle_control_center_clean_data(manage_sh)
    elif up == "Z": handle_control_center_uninstall(manage_sh)
    elif up == "A": handle_control_center_multi_account(manage_sh)
    elif up == "M": handle_control_center_traffic(manage_sh)
    elif up in ["K", "D"]:
        cmd = "benchmark" if up == "K" else "restart-services"
        subprocess.run(["bash", manage_sh, cmd], check=False)
        input("\nPress Enter to return to Control Center...")
    else:
        print(f"{RED}[ERROR] Unrecognized option '{choice}'.{NC}")
        input("\nPress Enter to continue...")
