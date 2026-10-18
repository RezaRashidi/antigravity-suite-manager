"""
Migration configuration paths, color codes, and logging utilities.
"""

from __future__ import annotations

import os
import sys

REAL_USER = os.environ.get("REAL_USER") or os.environ.get("SUDO_USER") or os.environ.get("USER") or "root"
_env_h = os.environ.get("REAL_HOME")
if _env_h:
    REAL_HOME = _env_h
elif REAL_USER and REAL_USER != "root":
    try:
        import pwd
        REAL_HOME = pwd.getpwnam(REAL_USER).pw_dir
    except Exception:
        REAL_HOME = os.path.expanduser("~")
else:
    REAL_HOME = os.path.expanduser("~")

GEMINI_DIR = os.path.join(REAL_HOME, ".gemini")
MASTER_GEMINI = os.path.join(GEMINI_DIR, "antigravity")
CONFIG_DIR = os.path.join(GEMINI_DIR, "config")
AGENTS_DIR = os.path.join(REAL_HOME, ".agents")
ANTIGRAVITY_CONF_DIR = os.path.join(REAL_HOME, ".config", "antigravity")
BACKUPS_DIR = os.path.join(ANTIGRAVITY_CONF_DIR, "backups")
LOCAL_BIN = os.path.join(REAL_HOME, ".local", "bin")

GREEN, BLUE, YELLOW, RED, CYAN, NC, BOLD = "\033[1;32m", "\033[1;38;5;75m", "\033[1;33m", "\033[1;31m", "\033[1;36m", "\033[0m", "\033[1m"


def get_master_gemini() -> str:
    m = sys.modules.get("antigravity-migration")
    return getattr(m, "MASTER_GEMINI", MASTER_GEMINI) if m else MASTER_GEMINI


def get_gemini_dir() -> str:
    m = sys.modules.get("antigravity-migration")
    return getattr(m, "GEMINI_DIR", GEMINI_DIR) if m else GEMINI_DIR


def log_info(msg: str) -> None: print(f"{BLUE}[INFO]{NC} {msg}")
def log_success(msg: str) -> None: print(f"{GREEN}[SUCCESS]{NC} {msg}")
def log_warn(msg: str) -> None: print(f"{YELLOW}[WARN]{NC} {msg}")
def log_err(msg: str) -> None: print(f"{RED}[ERROR]{NC} {msg}")
