"""
Interactive Control Center terminal loop for Antigravity Suite Manager.
"""

from __future__ import annotations

import os
from antigravity_suite.detect.configure_unified import configure_unified_instance
from antigravity_suite.detect.constants import REAL_HOME
from antigravity_suite.detect.control_center_dispatch import dispatch_control_center_choice
from antigravity_suite.detect.control_center_render import render_control_center_overview
from antigravity_suite.detect.paths_config import save_paths_config
from antigravity_suite.detect.unified import get_unified_instances

__all__ = ["render_control_center_overview", "run_control_center"]


def run_control_center() -> None:
    local_bin = os.path.join(REAL_HOME, ".local", "bin")
    manage_sh = os.path.join(local_bin, "manage-antigravity.sh")
    if not os.path.isfile(manage_sh):
        manage_sh = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bin", "manage-antigravity.sh")
    installer_sh = os.path.join(os.path.dirname(manage_sh), "..", "install.sh")

    while True:
        unified, curr_app, curr_ide, custom_paths = get_unified_instances()
        render_control_center_overview(unified)
        try:
            choice = input(f"Select option [1-{len(unified)}, A-Z, Default: Q]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice in ["0", "", "q", "Q", "exit"]:
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(unified):
            curr_app, curr_ide = configure_unified_instance(unified[int(choice) - 1], curr_app, curr_ide, custom_paths)
            save_paths_config(curr_app, curr_ide, custom_paths)
        else:
            dispatch_control_center_choice(choice, manage_sh, installer_sh, local_bin, unified)
