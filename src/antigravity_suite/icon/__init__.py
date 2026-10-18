"""
Icon Management and Window Customization Package.
"""

from antigravity_suite.icon.cardinal import get_icon_data, icon_cache, png_to_cardinal_array
from antigravity_suite.icon.generator import main as generate_icons_main
from antigravity_suite.icon.paths import (
    ACC1_ICON_PATH,
    ACC1_TRAY_PATH,
    ACC2_ICON_PATH,
    ACC2_TRAY_PATH,
    IDE_ICON_PATH,
    REAL_HOME,
    REAL_USER,
)
from antigravity_suite.icon.png_reconstruct import reconstruct_png
from antigravity_suite.icon.png_writer import resample_raw, write_png
from antigravity_suite.icon.proc import _BOOT_TIME, _CLK_TCK, get_boot_time, get_proc_start_time
from antigravity_suite.icon.recolor import recolor_emblem
from antigravity_suite.icon.tray_sync import sync_tray_cache
from antigravity_suite.icon.x11_apply import apply_icon_to_windows
from antigravity_suite.icon.x11_focus import focus_window

__all__ = [
    "REAL_USER", "REAL_HOME", "ACC1_ICON_PATH", "ACC2_ICON_PATH", "IDE_ICON_PATH",
    "ACC1_TRAY_PATH", "ACC2_TRAY_PATH", "_BOOT_TIME", "_CLK_TCK", "get_boot_time",
    "get_proc_start_time", "reconstruct_png", "write_png", "resample_raw",
    "png_to_cardinal_array", "icon_cache", "get_icon_data", "sync_tray_cache",
    "focus_window", "apply_icon_to_windows", "recolor_emblem", "generate_icons_main",
]
