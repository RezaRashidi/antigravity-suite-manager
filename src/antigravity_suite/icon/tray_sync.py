"""
Tray cache synchronization for Chromium status icons across temporary directories.
"""

from __future__ import annotations

import glob
import os
import shutil
import tempfile
from typing import List

from antigravity_suite.icon.paths import ACC1_ICON_PATH, ACC1_TRAY_PATH, ACC2_ICON_PATH, ACC2_TRAY_PATH
from antigravity_suite.icon.proc import _BOOT_TIME, _CLK_TCK, get_proc_start_time


def _get_temp_dirs() -> List[str]:
    cands = [tempfile.gettempdir(), "/tmp", "/var/tmp"]
    for env_k in ["TMPDIR", "TEMP", "TMP", "XDG_RUNTIME_DIR"]:
        v = os.environ.get(env_k)
        if v and os.path.isdir(v):
            cands.append(v)
    uid = getattr(os, "getuid", lambda: None)()
    if uid is not None and os.path.isdir(f"/run/user/{uid}"):
        cands.append(f"/run/user/{uid}")
    seen, valid = set(), []
    for c in cands:
        if c and os.path.isdir(c) and c not in seen:
            seen.add(c)
            valid.append(c)
    return valid


def _resolve_app_icon(cmd_low: str) -> str:
    import re
    m = re.search(r"antigravity-app-([a-z0-9_-]+)", cmd_low)
    if m:
        iid = m.group(1)
        icons = os.path.expanduser("~/.local/share/icons")
        for cand in [f"antigravity-app-{iid}-tray.png", f"antigravity-app-{iid}.png"]:
            p = os.path.join(icons, cand)
            if os.path.isfile(p): return p
    if any(k in cmd_low for k in ["profile2", "antigravity-2", "account2"]):
        return ACC2_TRAY_PATH if os.path.isfile(ACC2_TRAY_PATH) else ACC2_ICON_PATH
    return ACC1_TRAY_PATH if os.path.isfile(ACC1_TRAY_PATH) else ACC1_ICON_PATH


def _collect_processes():
    app_p, other_p = [], []
    for pid_str in os.listdir("/proc"):
        if not pid_str.isdigit(): continue
        try:
            with open(f"/proc/{pid_str}/cmdline", "rb") as f:
                cmd_low = f.read().decode("utf-8", errors="ignore").lower()
            pid = int(pid_str)
            st = get_proc_start_time(pid)
            proc_time = (_BOOT_TIME + (st / _CLK_TCK)) if st else os.path.getmtime(f"/proc/{pid_str}")

            if "antigravity" not in cmd_low:
                if any(x in cmd_low for x in ["chromium", "chrome", "code", "slack", "discord", "electron"]):
                    other_p.append((pid, proc_time))
            elif any(x in cmd_low for x in ["antigravity-ide", "antigravity_ide", "/antigravity-ide"]):
                other_p.append((pid, proc_time))
            else:
                app_p.append((pid, proc_time, _resolve_app_icon(cmd_low)))
        except Exception:
            pass
    return app_p, other_p


def sync_tray_cache() -> None:
    """Overwrites temporary Chromium tray cache with corresponding account icons."""
    app_p, other_p = _collect_processes()
    if not app_p: return

    chromium_dirs: List[str] = []
    for tdir in _get_temp_dirs():
        chromium_dirs.extend(glob.glob(os.path.join(tdir, "org.chromium.Chromium.*")))

    for d in chromium_dirs:
        if not os.path.isdir(d): continue
        try: dir_ctime = os.path.getctime(d)
        except Exception: continue

        diffo = min((abs(dir_ctime - t) for _, t in other_p), default=float("inf"))
        closest = min(app_p, key=lambda p: abs(dir_ctime - p[1]))
        diff_app = abs(dir_ctime - closest[1])

        if diff_app < diffo and os.path.isfile(closest[2]):
            target = closest[2]
            for icon_file in glob.glob(os.path.join(d, "status_icon_*.png")):
                try:
                    if not os.path.isfile(icon_file) or os.path.getsize(icon_file) != os.path.getsize(target):
                        shutil.copyfile(target, icon_file)
                except Exception: pass

