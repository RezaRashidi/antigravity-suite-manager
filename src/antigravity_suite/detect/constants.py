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


def get_suite_root_dir() -> str:
    """Finds the root directory of the Antigravity Suite Manager repository or installation."""
    env_dir = os.environ.get("ANTIGRAVITY_SUITE_DIR")
    if env_dir and os.path.isdir(env_dir):
        return env_dir

    # Detect relative to src/antigravity_suite/detect/constants.py (4 levels up to repo root)
    current = os.path.abspath(__file__)
    for _ in range(4):
        current = os.path.dirname(current)
    if os.path.isfile(os.path.join(current, "bin", "manage-antigravity.sh")) or os.path.isfile(os.path.join(current, "install.sh")):
        return current

    # Fallback to standard installation dir
    standard_repo = os.path.join(REAL_HOME, ".antigravity-suite-manager")
    if os.path.isdir(standard_repo):
        return standard_repo

    return current


def get_bin_script(name: str) -> str:
    """Resolves an executable script path across ~/.local/bin, repository bin/, and standard locations."""
    # 1. Check ~/.local/bin/
    local_target = os.path.join(LOCAL_BIN, name)
    if os.path.isfile(local_target):
        return local_target

    # 2. Check repo root / bin /
    repo_target = os.path.join(get_suite_root_dir(), "bin", name)
    if os.path.isfile(repo_target):
        return repo_target

    # 3. Check repo root /
    direct_target = os.path.join(get_suite_root_dir(), name)
    if os.path.isfile(direct_target):
        return direct_target

    return local_target

