"""
HSV-based color transformation for icon emblem custom styling.
"""

from __future__ import annotations

import colorsys
from typing import Optional

_COLOR_MAP = {
    "violet": 0.52, "magenta": 0.52, "purple": 0.52,
    "blue": 0.60, "cyan": 0.60,
    "green": 0.32, "emerald": 0.32,
    "amber": 0.12, "gold": 0.12, "orange": 0.12,
    "red": 0.90, "ruby": 0.90,
}


def recolor_emblem(
    w: int, h: int, data_in: bytearray, is_white_bg: bool = False,
    color: str = "original", custom_hue: Optional[float] = None,
) -> bytearray:
    """Transforms emblem color in RGBA buffer according to target hue or preset."""
    if custom_hue is None and (not color or color == "original"):
        return bytearray(data_in)

    is_mono = (color in ("monochrome", "silver", "grey", "gray")) and (custom_hue is None)
    target_hue = float(custom_hue) if custom_hue is not None else _COLOR_MAP.get(color, 0.52)
    out = bytearray(len(data_in))

    for i in range(0, len(data_in), 4):
        r, g, b, a = data_in[i], data_in[i + 1], data_in[i + 2], data_in[i + 3]
        if a < 10:
            out[i : i + 4] = (r, g, b, a)
            continue
        h_val, s_val, v_val = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        if is_mono:
            val = int(v_val * 255) if (s_val > 0.08 and v_val > 0.08) else None
            out[i : i + 4] = (val, val, val, a) if val is not None else (r, g, b, a)
        elif s_val > 0.15 and v_val > 0.08:
            nr, ng, nb = colorsys.hsv_to_rgb(target_hue, min(1.0, s_val * 1.15), min(1.0, v_val * 1.08))
            out[i : i + 4] = (int(nr * 255), int(ng * 255), int(nb * 255), a)
        elif not is_white_bg and (0.04 < v_val < 0.22 and s_val < 0.25):
            nr, ng, nb = colorsys.hsv_to_rgb(target_hue, 0.40, v_val * 1.25)
            out[i : i + 4] = (int(nr * 255), int(ng * 255), int(nb * 255), a)
        else:
            out[i : i + 4] = (r, g, b, a)
    return out
