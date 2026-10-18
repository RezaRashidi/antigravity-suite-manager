"""
X11 CARDINAL serialization of icons for _NET_WM_ICON properties.
"""

from __future__ import annotations

import ctypes
import os
from typing import Any, Dict, List, Optional, Tuple
from antigravity_suite.icon.paths import REAL_HOME
from antigravity_suite.icon.png_reconstruct import reconstruct_png

icon_cache: Dict[str, Tuple[Any, int]] = {}


def png_to_cardinal_array(png_path: str) -> Optional[List[int]]:
    """Converts a PNG file into a multi-resolution X11 CARDINAL format array."""
    if not os.path.exists(png_path):
        return None
    all_data = []
    base_name = os.path.basename(png_path)
    hicolor_dir = os.path.join(REAL_HOME, ".local/share/icons/hicolor")
    sizes = [16, 24, 32, 48, 64, 128]
    orig_w, orig_h, orig_data = None, None, None

    for target_size in sizes:
        sz_path = os.path.join(hicolor_dir, f"{target_size}x{target_size}", "apps", base_name)
        if os.path.isfile(sz_path):
            tw, th, data = reconstruct_png(sz_path)
        else:
            if orig_data is None:
                orig_w, orig_h, orig_data = reconstruct_png(png_path)
            if not orig_data:
                continue
            tw = th = target_size
            data = bytearray(tw * th * 4)
            step_x, step_y = orig_w / tw, orig_h / th
            for ty in range(th):
                sy = int(ty * step_y)
                for tx in range(tw):
                    sx = int(tx * step_x)
                    s_idx = (sy * orig_w + sx) * 4
                    d_idx = (ty * tw + tx) * 4
                    data[d_idx : d_idx + 4] = orig_data[s_idx : s_idx + 4]

        if not data:
            continue
        all_data.append(tw)
        all_data.append(th)
        for i in range(0, len(data), 4):
            r, g, b, a = data[i], data[i + 1], data[i + 2], data[i + 3]
            all_data.append((a << 24) | (r << 16) | (g << 8) | b)

    return all_data


def get_icon_data(png_path: str) -> Tuple[Any, int]:
    """Caches and returns C-types cardinal array and element count for X11."""
    if png_path not in icon_cache:
        data = png_to_cardinal_array(png_path)
        if data:
            c_arr = (ctypes.c_ulong * len(data))(*data)
            icon_cache[png_path] = (c_arr, len(data))
        else:
            icon_cache[png_path] = (None, 0)
    return icon_cache[png_path]
