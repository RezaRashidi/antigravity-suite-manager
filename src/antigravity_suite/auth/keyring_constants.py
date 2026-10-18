"""
Keyring constants, color codes, and environment paths.
"""

from __future__ import annotations

import os
from pathlib import Path

GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[1;38;5;75m'
CYAN = '\033[1;36m'
RED = '\033[1;31m'
NC = '\033[0m'
BOLD = '\033[1m'

_real_u = os.environ.get("REAL_USER") or os.environ.get("SUDO_USER") or os.environ.get("USER") or os.environ.get("LOGNAME")
_env_h = os.environ.get("REAL_HOME")
if _env_h:
    REAL_HOME = _env_h
elif _real_u and _real_u != "root":
    try:
        import pwd
        REAL_HOME = pwd.getpwnam(_real_u).pw_dir
    except Exception:
        REAL_HOME = os.path.expanduser("~")
else:
    REAL_HOME = os.path.expanduser("~")

CONF_DIR = os.path.join(REAL_HOME, ".config", "antigravity")
KEYRING_CONF = os.path.join(CONF_DIR, "keyring.conf")
LOCAL_BIN = os.path.join(REAL_HOME, ".local", "bin")
PROFILE2_DIR = os.path.join(REAL_HOME, ".antigravity-profile2")
