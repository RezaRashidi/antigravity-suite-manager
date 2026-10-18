"""
X11 Window Icon and WM_CLASS property enforcement.
"""

from __future__ import annotations

import ctypes
import glob
import os
import re
import shutil
import subprocess
from antigravity_suite.icon.cardinal import get_icon_data
from antigravity_suite.icon.paths import ACC1_ICON_PATH, ACC2_ICON_PATH, IDE_ICON_PATH, REAL_HOME
from antigravity_suite.icon.tray_sync import sync_tray_cache


def _identify_custom(win_cmd: str, c1: str):
    m_app = re.search(r'\.antigravity-profile-(app-[a-zA-Z0-9_-]+)', win_cmd) or re.search(r'\.antigravity-profile-([a-zA-Z0-9_-]+)', win_cmd)
    if m_app and "profile2" not in m_app.group(0):
        return f"antigravity-{m_app.group(1)}" if not m_app.group(1).startswith("antigravity") else m_app.group(1)
    m_ide = re.search(r'\.antigravity-ide-profile-([a-zA-Z0-9_-]+)', win_cmd)
    if m_ide: return f"antigravity-ide-{m_ide.group(1)}"
    m_cls = re.search(r'--class[=\s]+"?([a-zA-Z0-9_-]+)"?', win_cmd)
    if m_cls and m_cls.group(1) not in ("antigravity", "antigravity-1", "antigravity-2", "antigravity-acc2", "antigravity-ide"):
        return m_cls.group(1)
    if c1 not in ("antigravity", "antigravity-1", "antigravity-2", "antigravity-acc2", "antigravity-ide"):
        return c1
    return None


def apply_icon_to_windows() -> None:
    """Discovers Antigravity windows and applies corresponding distinct icons and WM_CLASS."""
    sync_tray_cache()
    if not shutil.which("xwininfo"): return
    x11 = ctypes.CDLL('libX11.so.6')
    x11.XOpenDisplay.restype = ctypes.c_void_p
    display = x11.XOpenDisplay(None)
    if not display: return
    try:
        atom_icon, atom_cardinal = x11.XInternAtom(display, b'_NET_WM_ICON', False), x11.XInternAtom(display, b'CARDINAL', False)
        atom_class, atom_string = x11.XInternAtom(display, b'WM_CLASS', False), x11.XInternAtom(display, b'STRING', False)
        has_other = os.path.isdir(os.path.join(REAL_HOME, ".antigravity-profile2")) or os.path.isfile(os.path.join(REAL_HOME, ".local/bin/antigravity-acc2")) or bool(glob.glob(os.path.join(REAL_HOME, ".antigravity-profile-app-*")))
        cls_acc1, cls_acc2, cls_ide = (b'antigravity-1\0antigravity-1\0' if has_other else b'antigravity\0antigravity\0'), b'antigravity-2\0antigravity-2\0', b'antigravity-ide\0antigravity-ide\0'

        res = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True)
        patched = getattr(apply_icon_to_windows, "_patched_wids", set())

        for line in res.stdout.splitlines():
            m = re.search(r'(0x[0-9a-fA-F]+)\s+"([^"]*)":\s+\("([^"]*)"\s+"([^"]*)"\)', line)
            if not m: continue
            wid_str, title, c1, c2 = m.groups()
            c1_l, c2_l = c1.lower(), c2.lower()
            if any(b in c1_l or b in c2_l for b in ['chrome', 'chromium', 'firefox', 'brave', 'edge', 'opera', 'gedit', 'datagrip', 'gjs']): continue
            wid = int(wid_str, 16)
            pid_m = re.search(r'=\s*(\d+)', subprocess.run(['xprop', '-id', hex(wid), '_NET_WM_PID'], capture_output=True, text=True).stdout)
            win_cmd = ""
            if pid_m:
                try:
                    with open(f"/proc/{pid_m.group(1)}/cmdline", "rb") as cf: win_cmd = cf.read().decode("utf-8", errors="ignore").lower()
                except Exception: pass
            if win_cmd and any(b in win_cmd for b in ['google/chrome', 'chromium', 'firefox', 'brave']): continue
            if not (('antigravity' in c1_l) or ('antigravity' in c2_l) or ('antigravity' in win_cmd)): continue

            c_wm = _identify_custom(win_cmd, c1)
            if c_wm:
                if (wid, c_wm) in patched and c1 == c_wm: continue
                c_icon = os.path.join(REAL_HOME, ".local/share/icons", f"{c_wm}.png")
                if os.path.isfile(c_icon):
                    c_arr, l = get_icon_data(c_icon)
                    if c_arr:
                        cls_b = f"{c_wm}\0{c_wm}\0".encode("utf-8")
                        x11.XChangeProperty(display, wid, atom_icon, atom_cardinal, 32, 0, ctypes.cast(c_arr, ctypes.c_void_p), l)
                        x11.XChangeProperty(display, wid, atom_class, atom_string, 8, 0, cls_b, len(cls_b))
                        x11.XFlush(display); patched.add((wid, c_wm))
                continue

            target_cls = "antigravity-ide" if ("antigravity ide" in title.lower() or "antigravity-ide" in c1_l or "antigravity-ide" in win_cmd) else ("antigravity-2" if ("account 2" in title.lower() or "antigravity-2" in c1_l or "antigravity-profile2" in win_cmd) else ("antigravity-1" if has_other else "antigravity"))
            if (wid, target_cls) in patched and c1 == target_cls: continue
            icon_p = IDE_ICON_PATH if target_cls == "antigravity-ide" else (ACC2_ICON_PATH if target_cls == "antigravity-2" else ACC1_ICON_PATH)
            cls_data = cls_ide if target_cls == "antigravity-ide" else (cls_acc2 if target_cls == "antigravity-2" else cls_acc1)
            c_arr, l = get_icon_data(icon_p)
            if c_arr:
                x11.XChangeProperty(display, wid, atom_icon, atom_cardinal, 32, 0, ctypes.cast(c_arr, ctypes.c_void_p), l)
                x11.XChangeProperty(display, wid, atom_class, atom_string, 8, 0, cls_data, len(cls_data))
                x11.XFlush(display); patched.add((wid, target_cls))

        apply_icon_to_windows._patched_wids = patched
    finally:
        try: x11.XCloseDisplay(display)
        except Exception: pass
