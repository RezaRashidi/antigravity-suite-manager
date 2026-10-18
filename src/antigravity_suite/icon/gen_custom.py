"""
Single custom instance icon generation across hicolor resolutions.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from antigravity_suite.icon.gen_config import LOCAL_APPS, LOCAL_ICONS, SCALE_BIN
from antigravity_suite.icon.gen_scaling import RESOLUTIONS, scale_and_write
from antigravity_suite.icon.png_writer import write_png
from antigravity_suite.icon.recolor import recolor_emblem


def generate_custom_instance_icon(
    inst_name: str, inst_theme: str, custom_hue: float | None,
    rgba_black: bytearray, rgba_white: bytearray,
) -> None:
    """Generates custom instance icon with specified hue across all resolutions."""
    base_inst = rgba_white if inst_theme == "white" else rgba_black
    if custom_hue is not None:
        rgba_inst = recolor_emblem(1024, 1024, base_inst, is_white_bg=(inst_theme == "white"), custom_hue=custom_hue)
    else:
        rgba_inst = bytearray(base_inst)

    icon_fn = f"{inst_name}.png"
    write_png(1024, 1024, rgba_inst, os.path.join(LOCAL_ICONS, icon_fn))
    has_scaler = os.path.isfile(SCALE_BIN) and os.access(SCALE_BIN, os.X_OK)

    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_p = os.path.join(tmp_dir, f"raw_{inst_name}_1024.raw")
        with open(raw_p, "wb") as f:
            f.write(rgba_inst)
        for sz in RESOLUTIONS:
            t_dir = os.path.join(LOCAL_ICONS, "hicolor", f"{sz}x{sz}", "apps")
            os.makedirs(t_dir, exist_ok=True)
            scale_and_write(raw_p, rgba_inst, tmp_dir, sz, os.path.join(t_dir, icon_fn), has_scaler)

    subprocess.run(["gtk-update-icon-cache", "-f", "-t", os.path.join(LOCAL_ICONS, "hicolor")], check=False)
    subprocess.run(["update-desktop-database", LOCAL_APPS], check=False)
    print(f"[SUCCESS] Custom icon {icon_fn} created in all hicolor resolutions.")
