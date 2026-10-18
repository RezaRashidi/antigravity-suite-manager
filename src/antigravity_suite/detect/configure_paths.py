"""
Interactive path configuration menu across all detected installations.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from antigravity_suite.detect.configure_install import configure_single_installation
from antigravity_suite.detect.constants import BOLD, CYAN, GREEN, NC, PATHS_CONF, RED, YELLOW
from antigravity_suite.detect.inspectors import inspect_app_dir, inspect_ide_dir
from antigravity_suite.detect.paths_config import load_paths_config, save_paths_config
from antigravity_suite.detect.scan import scan_installations


def configure_paths_interactive(installs: List[Dict[str, Any]]) -> None:
    curr_app, curr_ide, custom_paths = load_paths_config()
    while True:
        installs = scan_installations()
        print(f"\n{CYAN}========================================================================================{NC}")
        print(f"{BOLD}{CYAN}                    Installed Antigravity Suite Manager                                 {NC}")
        print(f"{CYAN}========================================================================================{NC}")
        print(f"{BOLD}Detected Antigravity Installations on System ({len(installs)} found):{NC}")
        print(f"----------------------------------------------------------------------------------------")
        if installs:
            for idx, item in enumerate(installs, 1):
                ver = f"v{item['version']}" if item["version"] != "Unknown" else "Unknown"
                tags = []
                if curr_app and os.path.realpath(item["path"]) == os.path.realpath(curr_app):
                    tags.append(f"{GREEN}[Primary App Target]{NC}")
                if curr_ide and os.path.realpath(item["path"]) == os.path.realpath(curr_ide):
                    tags.append(f"{GREEN}[Primary IDE Target]{NC}")
                print(f"  [{idx}] {item['type']:<20} {ver:<10} in {item['path']} {' '.join(tags)}")
        else:
            print(f"  {YELLOW}None detected outside defaults.{NC}")
        print(f"----------------------------------------------------------------------------------------")
        print("  [C] Add / Register a Custom Antigravity Path\n  [R] Reset Primary Targets to Defaults\n  [0] Done / Save & Continue")
        try:
            choice = input(f"Select installation [1-{len(installs)}, C for custom, 0 to finish]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice in ["0", "", "q", "exit"]:
            save_paths_config(curr_app, curr_ide, custom_paths)
            print(f"{GREEN}[SUCCESS] Saved configuration to {PATHS_CONF}{NC}")
            break
        elif choice.upper() == "C":
            custom_p = input("\nEnter custom path to Antigravity installation: ").strip()
            if custom_p:
                custom_p = os.path.realpath(os.path.expanduser(custom_p))
                if not os.path.isdir(custom_p) and input(f"Directory {custom_p} missing. Create? [Y/n]: ").strip().lower() not in ["n", "no"]:
                    os.makedirs(custom_p, exist_ok=True)
                new_cand = inspect_app_dir(custom_p) or inspect_ide_dir(custom_p)
                if not new_cand:
                    t_ans = input("Is target for [1] Antigravity App or [2] Antigravity IDE? [Default: 1]: ").strip()
                    c_type = "Antigravity IDE" if t_ans == "2" else "Antigravity App"
                    new_cand = {
                        "type": c_type, "version": "Not installed yet", "path": custom_p,
                        "executable": os.path.join(custom_p, "antigravity-ide" if t_ans == "2" else "antigravity"),
                        "writable": os.access(custom_p, os.W_OK),
                    }
                if custom_p not in custom_paths: custom_paths.append(custom_p)
                save_paths_config(curr_app, curr_ide, custom_paths)
                print(f"{GREEN}[OK] Added {custom_p} to registered installations.{NC}")
                curr_app, curr_ide = configure_single_installation(new_cand, curr_app, curr_ide, custom_paths)
                save_paths_config(curr_app, curr_ide, custom_paths)
        elif choice.upper() == "R":
            curr_app, curr_ide = "/opt/antigravity2", "/opt/antigravity"
            save_paths_config(curr_app, curr_ide, custom_paths)
            print(f"{GREEN}[OK] Reset primary targets: App -> {curr_app}, IDE -> {curr_ide}{NC}")
        elif choice.isdigit() and 1 <= int(choice) <= len(installs):
            target = installs[int(choice) - 1]
            curr_app, curr_ide = configure_single_installation(target, curr_app, curr_ide, custom_paths)
            save_paths_config(curr_app, curr_ide, custom_paths)
        else:
            print(f"{RED}[ERROR] Invalid selection '{choice}'.{NC}")
