"""
Detection constants, environment paths, and terminal ANSI color formatting.
"""

from __future__ import annotations

import os

GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[1;38;5;75m'
CYAN = '\033[1;36m'
RED = '\033[1;31m'
NC = '\033[0m'
BOLD = '\033[1m'

REAL_USER = os.environ.get("REAL_USER") or os.environ.get("SUDO_USER") or os.environ.get("USER") or os.environ.get("LOGNAME")
REAL_HOME = os.environ.get("REAL_HOME")
if not REAL_HOME:
    if REAL_USER and REAL_USER != "root":
        try:
            import pwd
            REAL_HOME = pwd.getpwnam(REAL_USER).pw_dir
        except Exception:
            REAL_HOME = os.path.expanduser("~")
    else:
        REAL_HOME = os.path.expanduser("~")

CONF_DIR = os.path.join(REAL_HOME, ".config", "antigravity")
PATHS_CONF = os.path.join(CONF_DIR, "paths.conf")
LOCAL_BIN = os.path.join(REAL_HOME, ".local", "bin")
LOCAL_DESKTOP = os.path.join(REAL_HOME, ".local", "share", "applications")
LOCAL_ICONS = os.path.join(REAL_HOME, ".local", "share", "icons")
