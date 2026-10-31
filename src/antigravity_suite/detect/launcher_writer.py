"""
Desktop file and shell launcher creation routines.
"""

from __future__ import annotations

import os
import subprocess
import sys

from antigravity_suite.detect.constants import GREEN, NC, REAL_HOME, get_bin_script


def create_launcher_and_desktop(cmd_name: str, app_type: str, exe_target: str, install_dir: str) -> None:
    local_bin = os.path.join(REAL_HOME, ".local", "bin")
    local_apps = os.path.join(REAL_HOME, ".local", "share", "applications")
    os.makedirs(local_bin, exist_ok=True)
    os.makedirs(local_apps, exist_ok=True)

    launcher_path = os.path.join(local_bin, cmd_name)
    desktop_path = os.path.join(local_apps, f"{cmd_name}.desktop")
    udd_prefix = "Antigravity IDE" if "IDE" in app_type else "Antigravity"
    user_data_dir = os.path.join(REAL_HOME, ".config", f"{udd_prefix}-{cmd_name}")

    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write(f'exec "{exe_target}" --password-store=basic --user-data-dir="{user_data_dir}" --class="{cmd_name}" --name="{cmd_name}" "$@"\n')
    os.chmod(launcher_path, 0o755)

    icon_name = "antigravity-ide" if "IDE" in app_type else "antigravity-app"
    with open(desktop_path, "w", encoding="utf-8") as f:
        f.write(f"[Desktop Entry]\nName=Google Antigravity ({cmd_name})\n")
        f.write(f"Comment=Google Antigravity {app_type}\nExec={launcher_path} %U\n")
        f.write(f"Icon={icon_name}\nType=Application\nStartupWMClass={cmd_name}\n")
        f.write("Categories=Development;IDE;\nTerminal=false\n")
    os.chmod(desktop_path, 0o644)
    subprocess.run(["update-desktop-database", local_apps], check=False, stderr=subprocess.DEVNULL)
    print(f"{GREEN}[SUCCESS] Created launcher {launcher_path} and desktop entry {desktop_path}{NC}")


def toggle_keyring_for_path(install_dir: str) -> None:
    cache_f = os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable")
    is_normal = os.path.isfile(cache_f)
    print(f"\nCurrent Keyring Mode: {'Normal File Storage (Decoupled)' if is_normal else 'GNOME Keyring (Secret Service)'}")
    print("  [1] Switch to Normal File Storage (Bypasses GNOME Keyring - Recommended)")
    print("  [2] Switch to GNOME Keyring (Secret Service)")
    k_choice = input("Select storage mode [1-2]: ").strip()
    keyring_tool = get_bin_script("antigravity-keyring.py")
    if os.path.isfile(keyring_tool):
        mode = "normal" if k_choice == "1" else "gnome"
        subprocess.run([sys.executable, keyring_tool, "set", "all", mode], check=False)
