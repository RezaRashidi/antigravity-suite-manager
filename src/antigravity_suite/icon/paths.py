"""
Icon paths and resolution for Antigravity application instances.
"""

from __future__ import annotations

import os
from pathlib import Path

REAL_USER = os.environ.get("REAL_USER") or os.environ.get("SUDO_USER") or os.environ.get("USER") or "root"
_env_home = os.environ.get("REAL_HOME")
if _env_home:
    REAL_HOME = _env_home
elif REAL_USER and REAL_USER != "root":
    try:
        import pwd
        REAL_HOME = pwd.getpwnam(REAL_USER).pw_dir
    except Exception:
        REAL_HOME = os.path.expanduser("~")
else:
    REAL_HOME = os.path.expanduser("~")

ACC1_ICON_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity.png")
if not os.path.isfile(ACC1_ICON_PATH):
    ACC1_ICON_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity-1.png")

ACC2_ICON_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity-acc2.png")
IDE_ICON_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity-ide.png")

ACC1_TRAY_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity-1-tray.png")
if not os.path.isfile(ACC1_TRAY_PATH):
    ACC1_TRAY_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity-tray.png")
if not os.path.isfile(ACC1_TRAY_PATH):
    ACC1_TRAY_PATH = os.path.join(REAL_HOME, ".local/share/icons/hicolor/48x48/apps/antigravity-1-tray.png")
if not os.path.isfile(ACC1_TRAY_PATH):
    ACC1_TRAY_PATH = ACC1_ICON_PATH

ACC2_TRAY_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity-acc2-tray.png")
if not os.path.isfile(ACC2_TRAY_PATH):
    ACC2_TRAY_PATH = os.path.join(REAL_HOME, ".local/share/icons/hicolor/48x48/apps/antigravity-acc2-tray.png")
if not os.path.isfile(ACC2_TRAY_PATH):
    ACC2_TRAY_PATH = ACC2_ICON_PATH
