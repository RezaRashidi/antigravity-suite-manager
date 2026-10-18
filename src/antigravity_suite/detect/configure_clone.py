"""
Interactive configuration menu loop for a single clone or profile.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict

from antigravity_suite.detect.clone_actions import (
    handle_clone_binary_change,
    handle_clone_create_or_delete,
    handle_clone_profile_relocate,
)
from antigravity_suite.detect.clone_keyring_icon import regen_clone_icons, toggle_clone_keyring
from antigravity_suite.detect.constants import BLUE, BOLD, CYAN, GREEN, NC, REAL_HOME, YELLOW
from antigravity_suite.detect.history_toggle import safe_toggle_history_mode
from antigravity_suite.detect.launchers import get_launcher_binary
from antigravity_suite.detect.process import is_acc1_running, is_main_ide_running


def configure_single_clone(clone: Dict[str, Any]) -> None:
    local_bin = os.path.join(REAL_HOME, ".local", "bin")
    local_apps = os.path.join(REAL_HOME, ".local", "share", "applications")
    manage_sh = os.path.join(local_bin, "manage-antigravity.sh")
    if not os.path.isfile(manage_sh):
        manage_sh = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bin", "manage-antigravity.sh")

    while True:
        cid, p_dir = clone["id"], clone["profile_dir"]
        is_acc1, is_acc2, is_ide1 = (cid == "app1"), (cid == "app2"), (cid == "ide1")

        is_shared = True if is_acc1 else (os.path.islink(os.path.join(p_dir, "conversations")) if is_ide1 else os.path.islink(os.path.join(p_dir, ".gemini", "antigravity")))
        h_mode = "Primary Master Pool" if is_acc1 else ("Shared 3-Way Sync" if is_shared else "Isolated Private")

        cache_f = os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable") if is_acc1 else (
            os.path.join(REAL_HOME, ".gemide", "cache", "antigravity-keyring-unavailable") if is_ide1 else os.path.join(p_dir, ".gemini", "cache", "antigravity-keyring-unavailable")
        )
        is_normal = os.path.isfile(cache_f)
        k_mode = "Normal (File Storage)" if is_normal else "GNOME Keyring"

        running = is_acc1_running(REAL_HOME) if is_acc1 else (
            subprocess.run(["pgrep", "-f", "antigravity-profile2.*Antigravity"], capture_output=True).returncode == 0 if is_acc2 else (
                is_main_ide_running(REAL_HOME) if is_ide1 else subprocess.run(["pgrep", "-f", os.path.basename(p_dir)], capture_output=True).returncode == 0
            )
        )
        launcher_f = clone["launcher"]
        linked_bin = get_launcher_binary(launcher_f) if (launcher_f and os.path.isfile(launcher_f)) else "Default"

        print(f"\n{CYAN}----------------------------------------------------------------------------------------{NC}")
        print(f"{BOLD}{CYAN}  Configuring Account / Clone: {clone['name']}{NC}\n{CYAN}----------------------------------------------------------------------------------------{NC}")
        print(f"  • ID: {cid} | Role: {clone['role']} | Profile: {p_dir}")
        print(f"  • Binary: {linked_bin} | Status: {GREEN if running else NC}{'Running' if running else 'Stopped'}{NC}")
        print(f"  • History: {GREEN if is_shared else YELLOW}{h_mode}{NC} | Keyring: {GREEN if is_normal else BLUE}{k_mode}{NC}")
        print("  [1] Toggle History Sharing Mode\n  [2] Toggle Credential Storage Mode\n  [3] Change Linked Binary")
        print(f"  [4] Re-generate Desktop Launcher & Icons\n  [5] Relocate / Rename Profile Directory\n  [6] {'Create Clone' if (is_ide1 or is_acc1) else 'Delete Clone'}\n  [0] Done")
        try:
            choice = input("Select option [0-6, Default: 0]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice in ["0", "", "q", "exit"]:
            break
        elif choice == "1":
            safe_toggle_history_mode(is_ide1 or ("ide" in cid) or ("IDE" in clone.get("type", "")), is_acc1, is_shared, p_dir, local_bin, REAL_HOME, name=cid)
        elif choice == "2":
            toggle_clone_keyring(clone, launcher_f, cache_f, is_acc1, cid, is_normal, local_bin)
        elif choice == "3":
            handle_clone_binary_change(launcher_f)
        elif choice == "4":
            regen_clone_icons(clone, launcher_f, is_ide1, is_acc1, is_acc2, manage_sh, local_apps, REAL_HOME)
        elif choice == "5":
            handle_clone_profile_relocate(clone, launcher_f, p_dir, is_acc1, is_acc2)
        elif choice == "6":
            if handle_clone_create_or_delete(clone, launcher_f, p_dir, is_ide1, is_acc1, is_acc2, cid, manage_sh, local_apps):
                break
