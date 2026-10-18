"""
Interactive configuration menu for a single detected installation.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any, Dict, List, Tuple

from antigravity_suite.detect.constants import BOLD, CYAN, GREEN, NC, REAL_HOME, YELLOW
from antigravity_suite.detect.launchers import create_launcher_and_desktop, toggle_keyring_for_path


def configure_single_installation(item: Dict[str, Any], curr_app: str, curr_ide: str, custom_paths: List[str]) -> Tuple[str, str]:
    while True:
        is_p_app = bool(curr_app and os.path.realpath(item["path"]) == os.path.realpath(curr_app))
        is_p_ide = bool(curr_ide and os.path.realpath(item["path"]) == os.path.realpath(curr_ide))
        role_label = f"{GREEN}[Primary App Target]{NC}" if is_p_app else (f"{GREEN}[Primary IDE Target]{NC}" if is_p_ide else f"{YELLOW}[Secondary]{NC}")

        print(f"\n{CYAN}----------------------------------------------------------------------------------------{NC}")
        print(f"{BOLD}{CYAN}  Configuring: {item['type']} ({item['version']}) in {item['path']}{NC}")
        print(f"{CYAN}----------------------------------------------------------------------------------------{NC}")
        print(f"  • Type: {item['type']} | Version: {item['version']} | Role: {role_label}")
        print(f"  • Path: {item['path']} | Executable: {item['executable'] or 'None'}")
        print("  [1] Change / Relocate Installation Directory Path\n  [2] Set as Suite Target (Primary App / IDE)")
        print("  [3] Re-generate Desktop Launcher & Shortcut\n  [4] Toggle Credential Storage Mode")
        print("  [5] Download & Re-install Latest Binaries\n  [0] Done (Return to list)")
        try:
            sub_c = input("Select option [0-5, Default: 0]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if sub_c in ["0", "", "q", "exit"]:
            break
        elif sub_c == "1":
            old_p = item["path"]
            new_p = input(f"\nEnter new directory path [current: {old_p}]: ").strip()
            if new_p and new_p != old_p:
                new_p = os.path.realpath(os.path.expanduser(new_p))
                os.makedirs(new_p, exist_ok=True)
                if (os.path.isfile(os.path.join(old_p, "resources", "app.asar")) or os.path.isfile(os.path.join(old_p, "resources", "app", "product.json"))):
                    if input(f"Copy files from {old_p} to {new_p}? [Y/n]: ").strip().lower() not in ["n", "no"]:
                        subprocess.run(["cp", "-a", f"{old_p}/.", f"{new_p}/"], check=False)
                item["path"] = new_p
                exe_name = os.path.basename(item["executable"]) if item["executable"] else ("antigravity-ide" if "IDE" in item["type"] else "antigravity")
                item["executable"] = os.path.join(new_p, exe_name)
                item["writable"] = os.access(new_p, os.W_OK)
                if is_p_app: curr_app = new_p
                if is_p_ide: curr_ide = new_p
                if old_p in custom_paths: custom_paths.remove(old_p)
                if new_p not in custom_paths and new_p not in [curr_app, curr_ide]: custom_paths.append(new_p)
                print(f"{GREEN}[SUCCESS] Installation path updated to: {new_p}{NC}")
        elif sub_c == "2":
            r_ans = input("Choose role [1: Primary App, 2: Primary IDE, 3: Clear]: ").strip()
            if r_ans == "1": curr_app = item["path"]; print(f"{GREEN}[SUCCESS] Set as Primary App.{NC}")
            elif r_ans == "2": curr_ide = item["path"]; print(f"{GREEN}[SUCCESS] Set as Primary IDE.{NC}")
            elif r_ans == "3":
                if is_p_app: curr_app = ""
                if is_p_ide: curr_ide = ""
                print(f"{GREEN}[SUCCESS] Cleared primary role.{NC}")
        elif sub_c == "3":
            def_name = re.sub(r"[^a-z0-9_-]+", "-", item["type"].lower())
            cmd_name = input(f"Launcher command name [default: {def_name}]: ").strip() or def_name
            exe_target = item["executable"] if (item["executable"] and os.path.isfile(item["executable"])) else os.path.join(item["path"], "antigravity-ide" if "IDE" in item["type"] else "antigravity")
            create_launcher_and_desktop(cmd_name, item["type"], exe_target, item["path"])
        elif sub_c == "4":
            toggle_keyring_for_path(item["path"])
        elif sub_c == "5":
            c_type = "ide" if "IDE" in item["type"] else "app"
            manage_sh = os.path.join(REAL_HOME, ".local", "bin", "manage-antigravity.sh")
            if not os.path.isfile(manage_sh):
                manage_sh = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bin", "manage-antigravity.sh")
            flag = "--ide-dir" if c_type == "ide" else "--app-dir"
            subprocess.run(["bash", manage_sh, "install", c_type, flag, item["path"]], check=False)
    return curr_app, curr_ide
