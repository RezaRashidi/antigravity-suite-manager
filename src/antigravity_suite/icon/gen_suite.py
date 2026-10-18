"""
Full suite icon generation across all standard resolutions.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from antigravity_suite.icon.gen_config import LOCAL_APPS, LOCAL_ICONS, SCALE_BIN
from antigravity_suite.icon.gen_scaling import RESOLUTIONS, scale_and_write
from antigravity_suite.icon.paths import REAL_HOME
from antigravity_suite.icon.png_writer import write_png
from antigravity_suite.icon.recolor import recolor_emblem


def _write_dedicated_tray(sz: int, name: str, s_data: bytearray) -> None:
    if sz == 48 and name in ("antigravity-1-tray.png", "antigravity-tray.png", "antigravity-acc2-tray.png"):
        write_png(48, 48, s_data, os.path.join(LOCAL_ICONS, name))
        s_dir = os.path.join(LOCAL_ICONS, "hicolor", "48x48", "status")
        os.makedirs(s_dir, exist_ok=True)
        write_png(48, 48, s_data, os.path.join(s_dir, name))
    elif sz in (24, 32) and name in ("antigravity-1-tray.png", "antigravity-tray.png", "antigravity-acc2-tray.png"):
        write_png(sz, sz, s_data, os.path.join(LOCAL_ICONS, f"{name[:-4]}-{sz}.png"))
        s_dir = os.path.join(LOCAL_ICONS, "hicolor", f"{sz}x{sz}", "status")
        os.makedirs(s_dir, exist_ok=True)
        write_png(sz, sz, s_data, os.path.join(s_dir, name))


def generate_suite_icons(
    acc1_theme: str, acc1_color: str, acc2_theme: str, acc2_color: str,
    ide_theme: str, ide_color: str, rgba_black: bytearray, rgba_white: bytearray,
) -> None:
    """Generates complete icon set for App1, App2, and IDE across all themes."""
    r_acc1 = recolor_emblem(1024, 1024, rgba_white if acc1_theme == "white" else rgba_black, is_white_bg=(acc1_theme == "white"), color=acc1_color)
    r_acc2 = recolor_emblem(1024, 1024, rgba_white if acc2_theme == "white" else rgba_black, is_white_bg=(acc2_theme == "white"), color=acc2_color)
    r_ide = recolor_emblem(1024, 1024, rgba_white if ide_theme == "white" else rgba_black, is_white_bg=(ide_theme == "white"), color=ide_color)

    for n, data in [("antigravity.png", r_acc1), ("antigravity-1.png", r_acc1), ("antigravity-tray.png", r_acc1), ("antigravity-1-tray.png", r_acc1), ("antigravity-acc2.png", r_acc2), ("antigravity-acc2-tray.png", r_acc2), ("antigravity-ide.png", r_ide)]:
        write_png(1024, 1024, data, os.path.join(LOCAL_ICONS, n))

    has_scaler = os.path.isfile(SCALE_BIN) and os.access(SCALE_BIN, os.X_OK)
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_map = {"antigravity.png": r_acc1, "antigravity-1.png": r_acc1, "antigravity-tray.png": r_acc1, "antigravity-1-tray.png": r_acc1, "antigravity-acc2.png": r_acc2, "antigravity-acc2-tray.png": r_acc2, "antigravity-ide.png": r_ide}
        paths_map = {}
        for n, d in raw_map.items():
            rp = os.path.join(tmp_dir, f"raw_{n}.raw")
            if not os.path.exists(rp):
                with open(rp, "wb") as f: f.write(d)
            paths_map[n] = rp

        for sz in RESOLUTIONS:
            t_dir = os.path.join(LOCAL_ICONS, "hicolor", f"{sz}x{sz}", "apps")
            os.makedirs(t_dir, exist_ok=True)
            for n, d in raw_map.items():
                s_data = scale_and_write(paths_map[n], d, tmp_dir, sz, os.path.join(t_dir, n), has_scaler)
                _write_dedicated_tray(sz, n, s_data)

    idx = os.path.join(LOCAL_ICONS, "hicolor", "index.theme")
    if not os.path.isfile(idx) and os.path.isfile("/usr/share/icons/hicolor/index.theme"):
        try: shutil.copy2("/usr/share/icons/hicolor/index.theme", idx)
        except Exception: pass

    pm_dir = os.path.join(REAL_HOME, ".local/share/pixmaps")
    os.makedirs(pm_dir, exist_ok=True)
    for n in ["antigravity.png", "antigravity-1.png", "antigravity-tray.png", "antigravity-1-tray.png", "antigravity-ide.png", "antigravity-acc2.png", "antigravity-acc2-tray.png"]:
        src_f = os.path.join(LOCAL_ICONS, n)
        if os.path.isfile(src_f):
            try: shutil.copy2(src_f, os.path.join(pm_dir, n))
            except Exception: pass

    subprocess.run(["gtk-update-icon-cache", "-f", "-t", os.path.join(LOCAL_ICONS, "hicolor")], check=False)
    subprocess.run(["update-desktop-database", LOCAL_APPS], check=False)
    apply_s = os.path.join(REAL_HOME, ".local/bin/antigravity-apply-icon.py")
    if os.path.isfile(apply_s): subprocess.run(["python3", apply_s], check=False)
    print("[SUCCESS] All desktop caches and live window icons updated.")
