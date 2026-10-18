"""
Scanning of Primary IDE and custom IDE clones/profiles.
"""

from __future__ import annotations

import glob
import os
import subprocess
from typing import Any, Dict, List

from antigravity_suite.detect.constants import REAL_HOME
from antigravity_suite.detect.process import is_main_ide_running


def scan_ide_clones(curr_ide: str = "", real_home: str | None = None) -> List[Dict[str, Any]]:
    home = real_home or REAL_HOME
    local_bin = os.path.join(home, ".local", "bin")
    local_apps = os.path.join(home, ".local", "share", "applications")
    clones: List[Dict[str, Any]] = []

    ide_profile = os.path.join(home, ".gemini", "antigravity-ide")
    ide_launcher = os.path.join(local_bin, "antigravity-ide")
    ide_desktop = os.path.join(local_apps, "antigravity-ide.desktop")
    ide_running = is_main_ide_running(home)
    ide_shared = os.path.islink(os.path.join(ide_profile, "conversations"))
    ide_cache = os.path.join(home, ".gemide", "cache", "antigravity-keyring-unavailable")
    if not os.path.isfile(ide_cache):
        ide_cache = os.path.join(home, ".gemini", "antigravity-ide", "cache", "antigravity-keyring-unavailable")

    if os.path.isfile(ide_launcher) or os.path.isfile(ide_desktop) or (curr_ide and os.path.isdir(curr_ide)):
        clones.append({
            "id": "ide1",
            "name": "Antigravity IDE (Primary)",
            "type": "IDE",
            "role": "Primary IDE",
            "profile_dir": ide_profile,
            "launcher": ide_launcher if os.path.isfile(ide_launcher) else (curr_ide if os.path.isdir(curr_ide) else "Default binary"),
            "desktop": ide_desktop,
            "wm_class": "antigravity-ide",
            "history_mode": "Shared 3-Way Sync" if ide_shared else "Isolated Private",
            "keyring_mode": "Normal (File Storage)" if os.path.isfile(ide_cache) else "GNOME Keyring",
            "status": "Running" if ide_running else "Stopped",
        })

    for p in sorted(glob.glob(os.path.join(home, ".antigravity-ide-profile-*"))):
        if ".bak" in p or ".removed" in p:
            continue
        cname = os.path.basename(p).replace(".antigravity-ide-profile-", "")
        c_running = subprocess.run(["pgrep", "-f", f"{os.path.basename(p)}"], capture_output=True).returncode == 0
        c_shared = os.path.islink(os.path.join(p, ".gemini", "antigravity-ide", "conversations")) or os.path.islink(os.path.join(p, ".gemini", "antigravity-ide"))
        c_cache = os.path.join(p, ".gemini", "cache", "antigravity-keyring-unavailable")
        clones.append({
            "id": f"ide-{cname}",
            "name": f"Antigravity IDE ({cname})",
            "type": "IDE Clone",
            "role": f"Custom IDE ({cname})",
            "profile_dir": p,
            "launcher": os.path.join(local_bin, f"antigravity-ide-{cname}"),
            "desktop": os.path.join(local_apps, f"antigravity-ide-{cname}.desktop"),
            "wm_class": f"antigravity-ide-{cname}",
            "history_mode": "Shared 3-Way Sync" if c_shared else "Isolated Private",
            "keyring_mode": "Normal (File Storage)" if os.path.isfile(c_cache) else "GNOME Keyring",
            "status": "Running" if c_running else "Stopped",
        })

    return clones
