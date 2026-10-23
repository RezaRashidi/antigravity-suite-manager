"""
Configuration persistence for Antigravity Cloud Sync.
"""

from __future__ import annotations

import os

from antigravity_suite.cloud.constants import CONFIG_DIR, CONFIG_FILE, DEFAULT_REMOTE


def load_remote_name() -> str:
    """Retrieves the configured cloud remote name."""
    env_rem = os.environ.get("ANTIGRAVITY_CLOUD_REMOTE")
    if env_rem:
        return env_rem.rstrip(":")

    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("REMOTE_NAME="):
                        val = line.split("=", 1)[1].strip().strip("\"'").rstrip(":")
                        if val:
                            return val
        except Exception:
            pass
    return DEFAULT_REMOTE


def save_remote_name(remote_name: str) -> str:
    """Saves the cloud remote name to config file."""
    clean_name = remote_name.strip().rstrip(":")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write("# Antigravity Suite Cloud Sync Configuration\n")
        f.write(f'REMOTE_NAME="{clean_name}"\n')
    return clean_name
