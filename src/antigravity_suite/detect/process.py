"""
Process detection for Antigravity App and IDE instances.
"""

from __future__ import annotations

import glob
import os
import subprocess
from typing import Set

from antigravity_suite.detect.constants import REAL_HOME


def is_acc1_running(real_home: str | None = None) -> bool:
    home = real_home or REAL_HOME
    target_udd = os.path.realpath(f"{home}/.config/Antigravity")
    try:
        cmd = ["pgrep", "-f", "Antigravity"]
        pids = subprocess.run(cmd, capture_output=True, text=True).stdout.strip().split()
        for pid in pids:
            try:
                with open(f"/proc/{pid}/cmdline", "r", errors="ignore") as f:
                    cmd_parts = [p for p in f.read().split("\x00") if p]
                    if not cmd_parts:
                        continue
                    udd = next((p.split("=", 1)[1] for p in cmd_parts if p.startswith("--user-data-dir=")), None)
                    if udd:
                        if os.path.realpath(os.path.expanduser(udd)) == target_udd:
                            return True
                    else:
                        cmd_line = " ".join(cmd_parts)
                        if "antigravity-profile" not in cmd_line and "Antigravity" in cmd_line:
                            if not any(arg.startswith("--user-data-dir=") for arg in cmd_parts):
                                return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def is_main_ide_running(real_home: str | None = None) -> bool:
    home = real_home or REAL_HOME
    target_udds = {
        os.path.realpath(f"{home}/.config/Antigravity IDE"),
        os.path.realpath(f"{home}/.antigravity-ide"),
    }
    try:
        cmd = ["pgrep", "-f", "antigravity-ide"]
        pids = subprocess.run(cmd, capture_output=True, text=True).stdout.strip().split()
        for pid in pids:
            try:
                with open(f"/proc/{pid}/cmdline", "r", errors="ignore") as f:
                    cmd_parts = [p for p in f.read().split("\x00") if p]
                    if not cmd_parts:
                        continue
                    cmd_line = " ".join(cmd_parts)
                    if ".antigravity-ide-profile-" in cmd_line or "antigravity-ide-profile" in cmd_line:
                        continue
                    udd = next((p.split("=", 1)[1] for p in cmd_parts if p.startswith("--user-data-dir=")), None)
                    if udd:
                        if os.path.realpath(os.path.expanduser(udd)) in target_udds:
                            return True
                    else:
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def get_running_paths() -> Set[str]:
    paths: Set[str] = set()
    try:
        for pid_dir in glob.glob("/proc/[0-9]*"):
            try:
                exe = os.path.realpath(os.path.join(pid_dir, "exe"))
                if "antigravity" in exe.lower():
                    paths.add(exe)
            except Exception:
                continue
    except Exception:
        pass
    return paths
