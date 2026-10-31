"""
Interactive configuration controller for unified instances.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Tuple

from antigravity_suite.detect.clone_actions import (
    handle_clone_binary_change,
    handle_clone_create_or_delete,
    handle_clone_profile_relocate,
)
from antigravity_suite.detect.clone_keyring_icon import regen_clone_icons, toggle_clone_keyring
from antigravity_suite.detect.configure_unified_menu import render_unified_header
from antigravity_suite.detect.constants import GREEN, NC, REAL_HOME, YELLOW, get_bin_script
from antigravity_suite.detect.history_toggle import safe_toggle_history_mode
from antigravity_suite.detect.inspectors import inspect_app_dir, inspect_ide_dir
from antigravity_suite.detect.launchers import create_launcher_and_desktop, get_launcher_binary, toggle_keyring_for_path
from antigravity_suite.detect.paths_config import save_paths_config
from antigravity_suite.detect.process import is_acc1_running, is_main_ide_running
from antigravity_suite.detect.unified_actions import (
    handle_unified_engine_relocate,
    handle_unified_patches_and_reinstall,
    handle_unified_target_role,
)


def configure_unified_instance(u_item: Dict[str, Any], curr_app: str, curr_ide: str, custom_paths: List[str]) -> Tuple[str, str]:
    local_bin = os.path.join(REAL_HOME, ".local", "bin")
    local_apps = os.path.join(REAL_HOME, ".local", "share", "applications")
    manage_sh = get_bin_script("manage-antigravity.sh")

    while True:
        c, eng = u_item.get("clone"), u_item.get("engine")
        cid, p_dir = (c["id"], c["profile_dir"]) if c else ("", "")
        is_acc1, is_acc2, is_ide1 = (cid == "app1"), (cid == "app2"), (cid == "ide1")

        is_shared = True if is_acc1 else (os.path.islink(os.path.join(p_dir, "conversations")) if is_ide1 else (os.path.islink(os.path.join(p_dir, ".gemini", "antigravity")) if c else False))
        h_mode = "Master Shared Pool" if is_acc1 else ("Shared 3-Way Sync" if is_shared else ("Isolated Private" if c else "N/A"))

        launcher_f = c["launcher"] if c else ""
        has_flag = os.path.isfile(launcher_f) and ("--password-store=basic" in open(launcher_f, errors="ignore").read())
        cache_f = os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable") if (is_acc1 or not c) else (
            os.path.join(REAL_HOME, ".gemide", "cache", "antigravity-keyring-unavailable") if is_ide1 else os.path.join(p_dir, ".gemini", "cache", "antigravity-keyring-unavailable")
        )
        is_normal = os.path.isfile(cache_f) or has_flag
        k_mode = "Normal (File Storage)" if is_normal else "GNOME Keyring"

        running = is_acc1_running(REAL_HOME) if is_acc1 else (
            subprocess.run(["pgrep", "-f", "antigravity-profile2.*Antigravity"], capture_output=True).returncode == 0 if is_acc2 else (
                is_main_ide_running(REAL_HOME) if is_ide1 else (subprocess.run(["pgrep", "-f", os.path.basename(p_dir)], capture_output=True).returncode == 0 if c else False)
            )
        )
        linked_bin = get_launcher_binary(launcher_f) if (launcher_f and os.path.isfile(launcher_f)) else ""
        eng_p = u_item.get("engine_path", "")
        fresh_eng = inspect_ide_dir(eng_p) if (u_item.get("type") and "IDE" in u_item["type"]) else inspect_app_dir(eng_p)
        if fresh_eng:
            eng, u_item["version"] = fresh_eng, fresh_eng.get("version", "Unknown")

        is_p_app = bool(curr_app and os.path.realpath(eng_p) == os.path.realpath(curr_app))
        is_p_ide = bool(curr_ide and os.path.realpath(eng_p) == os.path.realpath(curr_ide))
        role_label = f"{GREEN}[Primary App Target]{NC}" if is_p_app else (f"{GREEN}[Primary IDE Target]{NC}" if is_p_ide else f"{YELLOW}[Secondary Target]{NC}")

        render_unified_header(u_item, c, p_dir, launcher_f, is_shared, h_mode, is_normal, k_mode, running, eng_p, u_item.get("version", "Unknown"), role_label, linked_bin, eng)
        try: choice = input("Select option [Default: 0]: ").strip()
        except (KeyboardInterrupt, EOFError): break

        if choice in ["0", "", "q", "exit"]: break
        if c:
            if choice == "1": safe_toggle_history_mode(is_ide1 or ("ide" in cid) or ("IDE" in u_item.get("type", "")), is_acc1, is_shared, p_dir, local_bin, REAL_HOME, name=cid)
            elif choice == "2": toggle_clone_keyring(c, launcher_f, cache_f, is_acc1, cid, is_normal, local_bin)
            elif choice == "3": handle_clone_binary_change(launcher_f)
            elif choice == "4": regen_clone_icons(c, launcher_f, is_ide1, is_acc1, is_acc2, manage_sh, local_apps, REAL_HOME)
            elif choice == "5": handle_clone_profile_relocate(c, launcher_f, p_dir, is_acc1, is_acc2)
            elif choice == "6" and handle_clone_create_or_delete(c, launcher_f, p_dir, is_ide1, is_acc1, is_acc2, cid, manage_sh, local_apps): break
            elif choice == "7": eng_p, curr_app, curr_ide = handle_unified_engine_relocate(eng_p, is_p_app, is_p_ide, curr_app, curr_ide, custom_paths, launcher_f, u_item)
            elif choice == "8": handle_unified_patches_and_reinstall(choice, u_item, eng_p, manage_sh)
            elif choice == "9": curr_app, curr_ide = handle_unified_target_role(eng_p, is_p_app, is_p_ide, curr_app, curr_ide); save_paths_config(curr_app, curr_ide, custom_paths)
            elif choice.upper() in ["R", "F", "U", "T", "J", "CM", "MODELS", "Y"]: handle_unified_patches_and_reinstall(choice, u_item, eng_p, manage_sh)
        else:
            if choice == "1": eng_p, curr_app, curr_ide = handle_unified_engine_relocate(eng_p, is_p_app, is_p_ide, curr_app, curr_ide, custom_paths, launcher_f, u_item)
            elif choice == "2": curr_app, curr_ide = handle_unified_target_role(eng_p, is_p_app, is_p_ide, curr_app, curr_ide); save_paths_config(curr_app, curr_ide, custom_paths)
            elif choice == "3":
                cmd_name = input("Launcher command name: ").strip() or "antigravity-custom"
                create_launcher_and_desktop(cmd_name, u_item["type"], eng.get("executable") if eng else os.path.join(eng_p, "antigravity"), eng_p)
            elif choice == "4": toggle_keyring_for_path(eng_p)
            elif choice.upper() in ["5", "R", "F", "U", "T", "J", "CM", "MODELS", "Y"]: handle_unified_patches_and_reinstall(choice, u_item, eng_p, manage_sh)
    return curr_app, curr_ide
