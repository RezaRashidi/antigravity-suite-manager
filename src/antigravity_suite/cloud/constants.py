"""
Constants, configurations, and paths for Cloud Sync module.
"""

from __future__ import annotations

import os

REAL_HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(REAL_HOME, ".config", "antigravity")
CONFIG_FILE = os.path.join(CONFIG_DIR, "cloud_sync.conf")
DEFAULT_REMOTE = "agy-vault"

MASTER_GEMINI = os.path.join(REAL_HOME, ".gemini", "antigravity")
CONVERSATIONS_DIR = os.path.join(MASTER_GEMINI, "conversations")
BRAIN_DIR = os.path.join(MASTER_GEMINI, "brain")
ANNOTATIONS_DIR = os.path.join(MASTER_GEMINI, "annotations")

RCLONE_EXCLUDES = [
    "*-wal",
    "*-shm",
    "*.lock",
    "*.tmp",
    ".system_generated/tasks/**",
]

G = "\033[1;32m"
Y = "\033[1;33m"
R = "\033[1;31m"
B = "\033[1;34m"
C = "\033[1;36m"
NC = "\033[0m"
BOLD = "\033[1m"
