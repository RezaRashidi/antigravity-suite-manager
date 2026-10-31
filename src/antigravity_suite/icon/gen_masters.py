"""
Discovery and loading of master black and white icon assets.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from antigravity_suite.icon.gen_config import LOCAL_ICONS, SCALE_BIN
from antigravity_suite.icon.paths import REAL_HOME
from antigravity_suite.icon.png_reconstruct import reconstruct_png
from antigravity_suite.icon.png_writer import resample_raw


def ensure_scale_binary() -> None:
    """Auto-compiles scale_icon utility if binary is absent."""
    if not os.path.isfile(SCALE_BIN) or not os.access(SCALE_BIN, os.X_OK):
        from antigravity_suite.detect.constants import get_suite_root_dir
        candidates = [
            os.path.join(get_suite_root_dir(), "src", "scale_icon.c"),
            os.path.join(REAL_HOME, ".antigravity-suite-manager", "src", "scale_icon.c"),
        ]
        for sc in candidates:
            if os.path.isfile(sc) and shutil.which("gcc"):
                os.makedirs(os.path.dirname(SCALE_BIN), exist_ok=True)
                subprocess.run(["gcc", "-O3", sc, "-lm", "-o", SCALE_BIN], check=False)
                if os.path.isfile(SCALE_BIN):
                    try: os.chmod(SCALE_BIN, 0o755)
                    except Exception: pass
                    break


def load_master_icons():
    """Finds and rasterizes master black and white 1024x1024 icons."""
    from antigravity_suite.detect.paths_config import load_paths_config
    app_d, ide_d, _ = load_paths_config()
    b_cands = [
        os.path.join(LOCAL_ICONS, "antigravity-master-black.png"),
        os.path.join(app_d, "resources", "icon.png") if app_d else "",
        "/opt/Antigravity-x64/resources/icon.png", "/opt/antigravity2/resources/icon.png",
        "/opt/antigravity/resources/icon.png", "/usr/share/icons/antigravity.png",
    ]
    w_cands = [
        os.path.join(LOCAL_ICONS, "antigravity-master-white.png"),
        os.path.join(LOCAL_ICONS, "antigravity-ide-master.png"),
        os.path.join(ide_d, "resources", "app", "resources", "linux", "code.png") if ide_d else "",
        "/opt/antigravity-ide/resources/app/resources/linux/code.png",
    ]
    m_blk = next((c for c in b_cands if c and os.path.isfile(c)), None)
    m_wht = next((c for c in w_cands if c and os.path.isfile(c)), m_blk)
    if not m_blk:
        return None, None

    wb, hb, rb = reconstruct_png(m_blk)
    ww, hw, rw = reconstruct_png(m_wht) if m_wht else (None, None, None)

    if rb and (wb, hb) != (1024, 1024):
        rb = resample_raw(rb, wb, hb, 1024, 1024)
    if rw and (ww, hw) != (1024, 1024):
        rw = resample_raw(rw, ww, hw, 1024, 1024)

    if not rb and rw: rb = bytearray(rw)
    elif not rw and rb: rw = bytearray(rb)
    return rb, rw
