"""
Icon generator configuration and constant definitions.
"""

from __future__ import annotations

import os
from antigravity_suite.icon.paths import REAL_HOME

CONFIG_FILE = os.path.join(REAL_HOME, ".config", "antigravity", "icons.conf")
SCALE_BIN = os.path.join(REAL_HOME, ".antigravity-suite-manager", "bin", "scale_icon")
LOCAL_ICONS = os.path.join(REAL_HOME, ".local", "share", "icons")
LOCAL_APPS = os.path.join(REAL_HOME, ".local", "share", "applications")

COLOR_CHOICES = ["original", "violet", "blue", "green", "amber", "red", "monochrome"]


def load_icon_config() -> dict[str, str]:
    """Loads icon generation settings from icons.conf."""
    cfg = {
        "ACC1_ICON_THEME": "black", "ACC1_EMBLEM_COLOR": "original",
        "ACC2_ICON_THEME": "black", "ACC2_EMBLEM_COLOR": "violet",
        "ACC2_RECOLOR": "true", "IDE_ICON_THEME": "white",
        "IDE_EMBLEM_COLOR": "original",
    }
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        cfg[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass
    return cfg


def save_icon_config(acc1_theme: str, acc1_color: str, acc2_theme: str, acc2_color: str, acc2_recolor: str, ide_theme: str, ide_color: str) -> None:
    """Saves icon generation settings to icons.conf."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        f.write("# Antigravity Suite Icon Configuration\n")
        f.write(f'ACC1_ICON_THEME="{acc1_theme}"\n')
        f.write(f'ACC1_EMBLEM_COLOR="{acc1_color}"\n')
        f.write(f'ACC2_ICON_THEME="{acc2_theme}"\n')
        f.write(f'ACC2_EMBLEM_COLOR="{acc2_color}"\n')
        f.write(f'ACC2_RECOLOR="{acc2_recolor}"\n')
        f.write(f'IDE_ICON_THEME="{ide_theme}"\n')
        f.write(f'IDE_EMBLEM_COLOR="{ide_color}"\n')
    print(f"[INFO] Configuration saved to {CONFIG_FILE}")
