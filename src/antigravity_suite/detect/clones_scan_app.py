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


def _is_normal(cache_f: str, launcher_f: str, target: str) -> bool:
    if os.path.isfile(cache_f): return True
    if launcher_f and os.path.isfile(launcher_f):
        try:
            with open(launcher_f, "r", errors="ignore") as f:
                if "--password-store=basic" in f.read(): return True
        except Exception: pass
    k_conf = os.path.join(REAL_HOME, ".config", "antigravity", "keyring.conf")
    if os.path.isfile(k_conf):
        try:
            with open(k_conf, "r") as f: return f'KEYRING_MODE_{target.upper()}="normal"' in f.read()
        except Exception: pass
    return False


def scan_app_clones(curr_app: str = "", real_home: str | None = None) -> List[Dict[str, Any]]:
    home = real_home or REAL_HOME
    local_bin, local_apps = os.path.join(home, ".local", "bin"), os.path.join(home, ".local", "share", "applications")
    clones: List[Dict[str, Any]] = []

    acc2_profile, acc2_lnch, acc2_dt = os.path.join(home, ".antigravity-profile2"), os.path.join(local_bin, "antigravity-acc2"), os.path.join(local_apps, "antigravity-2.desktop")
    acc2_run = subprocess.run(["pgrep", "-f", "antigravity-profile2.*Antigravity"], capture_output=True).returncode == 0
    acc2_exists = (os.path.isfile(acc2_lnch) or os.path.isfile(acc2_dt) or acc2_run) and os.path.isdir(acc2_profile)

    custom_apps = [p for p in sorted(glob.glob(os.path.join(home, ".antigravity-profile-app-*"))) if ".bak" not in p and ".removed" not in p and os.path.isdir(p)]
    has_other = acc2_exists or bool(custom_apps)

    acc1_profile = os.path.join(home, ".gemini")
    acc1_lnch = os.path.join(local_bin, "antigravity" if not has_other else "antigravity-1")
    if not os.path.isfile(acc1_lnch):
        acc1_lnch = next((os.path.join(local_bin, f) for f in ["antigravity", "antigravity-1"] if os.path.isfile(os.path.join(local_bin, f))), acc1_lnch)
    acc1_dt = os.path.join(local_apps, "antigravity.desktop" if not has_other else "antigravity-1.desktop")
    if not os.path.isfile(acc1_dt):
        acc1_dt = next((os.path.join(local_apps, f) for f in ["antigravity.desktop", "antigravity-1.desktop"] if os.path.isfile(os.path.join(local_apps, f))), acc1_dt)

    acc1_run = is_acc1_running(home)
    acc1_cache = os.path.join(acc1_profile, "cache", "antigravity-keyring-unavailable")
    acc1_norm = _is_normal(acc1_cache, acc1_lnch, "app1")
    if acc1_norm and not os.path.isfile(acc1_cache):
        try:
            os.makedirs(os.path.dirname(acc1_cache), exist_ok=True); open(acc1_cache, "a").close()
        except Exception: pass

    if os.path.isfile(acc1_lnch) or os.path.isfile(acc1_dt) or (curr_app and os.path.isdir(curr_app)):
        clones.append({
            "id": "app1", "name": "Antigravity" if not has_other else "Antigravity (Account 1 - Default)",
            "type": "App", "role": "Primary Application" if not has_other else "Primary Account",
            "profile_dir": acc1_profile, "launcher": acc1_lnch if os.path.isfile(acc1_lnch) else (curr_app if os.path.isdir(curr_app) else "Default binary"),
            "desktop": acc1_dt, "wm_class": "antigravity" if not has_other else "antigravity-1",
            "history_mode": "Master Shared Pool", "keyring_mode": "Normal (File Storage)" if acc1_norm else "GNOME Keyring",
            "status": "Running" if acc1_run else "Stopped",
        })

    if acc2_exists:
        acc2_shared = os.path.islink(os.path.join(acc2_profile, ".gemini", "antigravity"))
        acc2_cache = os.path.join(acc2_profile, ".gemini", "cache", "antigravity-keyring-unavailable")
        acc2_norm = _is_normal(acc2_cache, acc2_lnch, "app2")
        clones.append({
            "id": "app2", "name": "Antigravity (Account 2)", "type": "App Clone", "role": "Secondary Account",
            "profile_dir": acc2_profile, "launcher": acc2_lnch, "desktop": acc2_dt, "wm_class": "antigravity-2",
            "history_mode": "Shared 3-Way Sync" if acc2_shared else "Isolated Private",
            "keyring_mode": "Normal (File Storage)" if acc2_norm else "GNOME Keyring",
            "status": "Running" if acc2_run else "Stopped",
        })

    for p in custom_apps:
        cname = os.path.basename(p).replace(".antigravity-profile-app-", "")
        c_run = subprocess.run(["pgrep", "-f", f"{os.path.basename(p)}.*Antigravity"], capture_output=True).returncode == 0
        c_shared = os.path.islink(os.path.join(p, ".gemini", "antigravity"))
        c_cache = os.path.join(p, ".gemini", "cache", "antigravity-keyring-unavailable")
        c_lnch = os.path.join(local_bin, f"antigravity-app-{cname}")
        clones.append({
            "id": f"app-{cname}", "name": f"Antigravity (App: {cname})", "type": "App Clone",
            "role": f"Custom Account ({cname})", "profile_dir": p, "launcher": c_lnch,
            "desktop": os.path.join(local_apps, f"antigravity-app-{cname}.desktop"),
            "wm_class": f"antigravity-app-{cname}", "history_mode": "Shared 3-Way Sync" if c_shared else "Isolated Private",
            "keyring_mode": "Normal (File Storage)" if _is_normal(c_cache, c_lnch, "app1") else "GNOME Keyring",
            "status": "Running" if c_run else "Stopped",
        })

    return clones
