"""
Tray cache synchronization for Chromium status icons.
"""

from __future__ import annotations

import glob
import os
import shutil
from antigravity_suite.icon.paths import ACC1_ICON_PATH, ACC1_TRAY_PATH, ACC2_ICON_PATH, ACC2_TRAY_PATH
from antigravity_suite.icon.proc import _BOOT_TIME, _CLK_TCK, get_proc_start_time


def _collect_processes():
    acc1_p, acc2_p, other_p = [], [], []
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
            elif "antigravity-ide" in cmd_low or "/opt/antigravity/" in cmd_low:
                other_p.append((pid, proc_time))
            elif any(k in cmd_low for k in ["antigravity-profile2", "antigravity-2", "account2"]):
                acc2_p.append((pid, proc_time))
            else:
                acc1_p.append((pid, proc_time))
        except Exception:
            pass
    return acc1_p, acc2_p, other_p


def sync_tray_cache() -> None:
    """Overwrites temporary Chromium tray cache with corresponding account icons."""
    eff_acc1 = ACC1_TRAY_PATH if os.path.isfile(ACC1_TRAY_PATH) else ACC1_ICON_PATH
    eff_acc2 = ACC2_TRAY_PATH if os.path.isfile(ACC2_TRAY_PATH) else ACC2_ICON_PATH
    acc1_p, acc2_p, other_p = _collect_processes()
    if not acc1_p and not acc2_p: return

    for d in glob.glob("/tmp/org.chromium.Chromium.*"):
        if not os.path.isdir(d): continue
        try: dir_ctime = os.path.getctime(d)
        except Exception: continue

        diff1 = min((abs(dir_ctime - t) for _, t in acc1_p), default=float("inf"))
        diff2 = min((abs(dir_ctime - t) for _, t in acc2_p), default=float("inf"))
        diffo = min((abs(dir_ctime - t) for _, t in other_p), default=float("inf"))

        target = None
        if diff1 < diff2 and diff1 < diffo: target = eff_acc1
        elif diff2 < diff1 and diff2 < diffo: target = eff_acc2
        elif diff1 != float("inf") and not acc2_p and diff1 <= diffo: target = eff_acc1
        elif diff2 != float("inf") and not acc1_p and diff2 <= diffo: target = eff_acc2

        if target and os.path.isfile(target):
            for icon_file in glob.glob(os.path.join(d, "status_icon_*.png")):
                try:
                    if not os.path.isfile(icon_file) or os.path.getsize(icon_file) != os.path.getsize(target):
                        shutil.copyfile(target, icon_file)
                except Exception: pass
