"""
Keyring and icon helper operations for clone configuration.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
from typing import Any, Dict

from antigravity_suite.detect.constants import GREEN, NC, get_bin_script
from antigravity_suite.detect.launchers import get_launcher_binary, update_launcher_binary


def toggle_clone_keyring(clone: Dict[str, Any], launcher_f: str, cache_f: str, is_acc1: bool, cid: str, is_normal: bool, local_bin: str) -> None:
    tool_py = get_bin_script("antigravity-keyring.py")
    new_mode = "gnome" if is_normal else "normal"
    if is_acc1: subprocess.run([sys.executable, tool_py, "set", "app1", new_mode], check=False)
    elif cid == "app2": subprocess.run([sys.executable, tool_py, "set", "app2", new_mode], check=False)
    elif "ide" in cid: subprocess.run([sys.executable, tool_py, "set", "ide", new_mode], check=False)
    else:
        os.makedirs(os.path.dirname(cache_f), exist_ok=True)
        if is_normal:
            try: os.remove(cache_f)
            except Exception: pass
            if launcher_f and os.path.isfile(launcher_f):
                with open(launcher_f, "r") as lf: cnt = lf.read().replace("--password-store=basic ", "").replace("--password-store=basic", "")
                with open(launcher_f, "w") as lf: lf.write(cnt)
        else:
            with open(cache_f, "w") as f: f.write("# Keyring bypassed\n")
            if launcher_f and os.path.isfile(launcher_f):
                with open(launcher_f, "r") as lf: cnt = lf.read()
                if "--password-store=basic" not in cnt:
                    new_l = [re.sub(r'^(\s*exec\s+("[^"]+"|\'[^\']+\'|\S+))(.*)$', r"\1 --password-store=basic\3", line) if line.strip().startswith("exec ") else line for line in cnt.splitlines()]
                    with open(launcher_f, "w") as lf: lf.write("\n".join(new_l) + "\n")
    print(f"{GREEN}[SUCCESS] Switched credential mode to {new_mode.upper()}.{NC}")


def regen_clone_icons(clone: Dict[str, Any], launcher_f: str, is_ide1: bool, is_acc1: bool, is_acc2: bool, manage_sh: str, local_apps: str, real_home: str) -> None:
    if os.path.isfile(manage_sh):
        if input(f"Customize Icon appearance for {clone['name']}? [y/N]: ").strip().lower() in ["y", "yes"]:
            target_arg = "ide" if is_ide1 else ("app2" if is_acc2 else ("app1" if is_acc1 else ""))
            cmd = ["bash", manage_sh, "set-icons"] + ([target_arg] if target_arg else [])
            subprocess.run(cmd, check=False)
        if is_acc2: subprocess.run(["bash", manage_sh, "app2"], check=False)
        elif is_acc1: subprocess.run(["bash", manage_sh, "app1"], check=False)
        elif is_ide1: subprocess.run(["bash", manage_sh, "ide-shortcuts"], check=False)

    if launcher_f and os.path.isfile(launcher_f) and (not get_launcher_binary(launcher_f) or not os.path.isfile(get_launcher_binary(launcher_f))):
        cand_exes = ["/opt/antigravity-ide/antigravity-ide", "/opt/antigravity/antigravity-ide"] if is_ide1 else ["/opt/Antigravity-x64/antigravity", "/opt/antigravity2/antigravity"]
        for ce in cand_exes:
            if os.path.isfile(ce):
                update_launcher_binary(launcher_f, ce)
                break
    has_acc2 = os.path.isdir(os.path.join(real_home, ".antigravity-profile2")) and os.path.isfile(os.path.join(real_home, ".local", "bin", "antigravity-acc2"))
    has_other = has_acc2 or bool(glob.glob(os.path.join(real_home, ".antigravity-profile-app-*")))
    dup_dt = os.path.join(local_apps, "antigravity.desktop" if has_other else "antigravity-1.desktop")
    try: os.remove(dup_dt)
    except Exception: pass
    subprocess.run(["update-desktop-database", local_apps], check=False, stderr=subprocess.DEVNULL)
    print(f"{GREEN}[SUCCESS] Regenerated desktop launcher and icons.{NC}")
