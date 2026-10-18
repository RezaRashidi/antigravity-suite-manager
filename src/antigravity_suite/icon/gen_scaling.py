"""
Multi-resolution icon image scaling helpers.
"""

from __future__ import annotations

import os
import subprocess
from antigravity_suite.icon.gen_config import SCALE_BIN
from antigravity_suite.icon.png_writer import resample_raw, write_png

RESOLUTIONS = [512, 256, 128, 64, 48, 32, 24, 16]


def scale_and_write(
    in_raw_path: str, rgba_1024: bytearray, tmp_dir: str,
    sz: int, dst_png: str, has_scaler: bool,
) -> bytearray:
    """Scales a 1024x1024 raw buffer to target size and writes to disk."""
    s_data = None
    if has_scaler:
        out_raw = os.path.join(tmp_dir, f"scaled_{sz}_{os.path.basename(dst_png)}.raw")
        try:
            subprocess.run([SCALE_BIN, in_raw_path, "1024", "1024", out_raw, str(sz), str(sz)], check=True)
            if os.path.isfile(out_raw):
                with open(out_raw, "rb") as rf:
                    s_data = rf.read()
        except Exception:
            pass
    if not s_data:
        s_data = resample_raw(rgba_1024, 1024, 1024, sz, sz)
    write_png(sz, sz, s_data, dst_png)
    return s_data
