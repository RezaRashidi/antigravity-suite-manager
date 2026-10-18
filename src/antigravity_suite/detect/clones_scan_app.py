"""
Scanning of Primary App and custom App clones/profiles.
"""

from __future__ import annotations

import glob
import os
import subprocess
from typing import Any, Dict, List

from antigravity_suite.detect.constants import REAL_HOME
from antigravity_suite.detect.process import is_acc1_running


def scan_app_clones(curr_app: str = "", real_home: str | None = None) -> List[Dict[str, Any]]:
    home = real_home or REAL_HOME
    local_bin, local_apps = os.path.join(home, ".local", "bin"), os.path.join(home, ".local", "share", "applications")
    clones: List[Dict[str, Any]] = []

    acc2_profile = os.path.join(home, ".antigravity-profile2")
    has_other = os.path.isdir(acc2_profile) or os.path.isfile(os.path.join(local_bin, "antigravity-acc2")) or any(
        os.path.isdir(p) and ".bak" not in p and ".removed" not in p for p in glob.glob(os.path.join(home, ".antigravity-profile-app-*"))
    )

    acc1_profile = os.path.join(home, ".gemini")
    acc1_lnch = os.path.join(local_bin, "antigravity" if not has_other else "antigravity-1")
    if not os.path.isfile(acc1_lnch):
        acc1_lnch = next((os.path.join(local_bin, f) for f in ["antigravity", "antigravity-1"] if os.path.isfile(os.path.join(local_bin, f))), acc1_lnch)
    acc1_dt = os.path.join(local_apps, "antigravity.desktop" if not has_other else "antigravity-1.desktop")
    if not os.path.isfile(acc1_dt):
        acc1_dt = next((os.path.join(local_apps, f) for f in ["antigravity.desktop", "antigravity-1.desktop"] if os.path.isfile(os.path.join(local_apps, f))), acc1_dt)

    acc1_run = is_acc1_running(home)
    acc1_cache = os.path.join(acc1_profile, "cache", "antigravity-keyring-unavailable")

    if os.path.isfile(acc1_lnch) or os.path.isfile(acc1_dt) or (curr_app and os.path.isdir(curr_app)):
        clones.append({
            "id": "app1", "name": "Antigravity" if not has_other else "Antigravity (Account 1 - Default)",
            "type": "App", "role": "Primary Application" if not has_other else "Primary Account",
            "profile_dir": acc1_profile, "launcher": acc1_lnch if os.path.isfile(acc1_lnch) else (curr_app if os.path.isdir(curr_app) else "Default binary"),
            "desktop": acc1_dt, "wm_class": "antigravity" if not has_other else "antigravity-1",
            "history_mode": "Master Shared Pool", "keyring_mode": "Normal (File Storage)" if os.path.isfile(acc1_cache) else "GNOME Keyring",
            "status": "Running" if acc1_run else "Stopped",
        })

    if os.path.isdir(acc2_profile) or os.path.isfile(os.path.join(local_bin, "antigravity-acc2")):
        acc2_run = subprocess.run(["pgrep", "-f", "antigravity-profile2.*Antigravity"], capture_output=True).returncode == 0
        acc2_shared = os.path.islink(os.path.join(acc2_profile, ".gemini", "antigravity"))
        acc2_cache = os.path.join(acc2_profile, ".gemini", "cache", "antigravity-keyring-unavailable")
        clones.append({
            "id": "app2", "name": "Antigravity (Account 2)", "type": "App Clone", "role": "Secondary Account",
            "profile_dir": acc2_profile, "launcher": os.path.join(local_bin, "antigravity-acc2"),
            "desktop": os.path.join(local_apps, "antigravity-2.desktop"), "wm_class": "antigravity-2",
            "history_mode": "Shared 3-Way Sync" if acc2_shared else "Isolated Private",
            "keyring_mode": "Normal (File Storage)" if os.path.isfile(acc2_cache) else "GNOME Keyring",
            "status": "Running" if acc2_run else "Stopped",
        })

    for p in sorted(glob.glob(os.path.join(home, ".antigravity-profile-app-*"))):
        if ".bak" in p or ".removed" in p:
            continue
        cname = os.path.basename(p).replace(".antigravity-profile-app-", "")
        c_run = subprocess.run(["pgrep", "-f", f"{os.path.basename(p)}.*Antigravity"], capture_output=True).returncode == 0
        c_shared = os.path.islink(os.path.join(p, ".gemini", "antigravity"))
        c_cache = os.path.join(p, ".gemini", "cache", "antigravity-keyring-unavailable")
        clones.append({
            "id": f"app-{cname}", "name": f"Antigravity (App: {cname})", "type": "App Clone",
            "role": f"Custom Account ({cname})", "profile_dir": p,
            "launcher": os.path.join(local_bin, f"antigravity-app-{cname}"),
            "desktop": os.path.join(local_apps, f"antigravity-app-{cname}.desktop"),
            "wm_class": f"antigravity-app-{cname}",
            "history_mode": "Shared 3-Way Sync" if c_shared else "Isolated Private",
            "keyring_mode": "Normal (File Storage)" if os.path.isfile(c_cache) else "GNOME Keyring",
            "status": "Running" if c_run else "Stopped",
        })

    return clones
