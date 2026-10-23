"""
Rclone binary invocation and remote validation adapter.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import List, Tuple

from antigravity_suite.cloud.constants import RCLONE_EXCLUDES


def is_rclone_installed() -> bool:
    """Checks whether rclone executable is found on PATH."""
    return shutil.which("rclone") is not None


def list_rclone_remotes() -> List[str]:
    """Returns list of configured rclone remotes."""
    if not is_rclone_installed():
        return []
    try:
        res = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return [line.strip().rstrip(":") for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    return []


def is_remote_configured(remote: str) -> bool:
    """Verifies if the specified remote name exists in rclone config."""
    clean = remote.strip().rstrip(":")
    return clean in list_rclone_remotes()


def rclone_copy_dir(src: str, dst: str, excludes: List[str] | None = None) -> Tuple[int, str]:
    """Executes 'rclone copy' with standard exclusions and update flags."""
    if not is_rclone_installed():
        return 127, "rclone binary not found"

    ex = excludes if excludes is not None else RCLONE_EXCLUDES
    cmd = ["rclone", "copy", src, dst, "--update", "--use-mtime"]
    for pattern in ex:
        cmd.extend(["--exclude", pattern])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return res.returncode, res.stderr or res.stdout
    except Exception as e:
        return 1, str(e)


def rclone_check_remote_alive(remote: str) -> bool:
    """Tests read connection to remote root directory."""
    if not is_remote_configured(remote):
        return False
    clean = f"{remote.strip().rstrip(':')}:"
    try:
        res = subprocess.run(["rclone", "lsd", clean, "--max-depth", "1"], capture_output=True, timeout=15)
        return res.returncode == 0
    except Exception:
        return False
