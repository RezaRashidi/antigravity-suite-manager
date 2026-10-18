"""
Safe history mode toggling coordinator with automated backup.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys

from antigravity_suite.detect.constants import NC, YELLOW
from antigravity_suite.detect.history_app_toggle import toggle_app_history
from antigravity_suite.detect.history_ide_toggle import toggle_ide_history


def safe_toggle_history_mode(is_ide: bool, is_acc1: bool, is_shared: bool, p_dir: str, local_bin: str, REAL_HOME: str, name: str = "") -> None:
    if is_acc1:
        print(f"{YELLOW}[NOTICE] Account 1 is the Master Shared Pool and cannot be isolated.{NC}")
        return

    shared_pool = os.path.join(REAL_HOME, ".gemini", "antigravity")
    os.makedirs(os.path.join(shared_pool, "conversations"), exist_ok=True)
    os.makedirs(os.path.join(shared_pool, "brain"), exist_ok=True)

    migration_tool = os.path.join(local_bin, "antigravity-migration.py")
    if not os.path.isfile(migration_tool):
        migration_tool = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bin", "antigravity-migration.py")
    if os.path.isfile(migration_tool):
        safe_label = f"pre_toggle_{name or 'instance'}"
        subprocess.run([sys.executable, migration_tool, "create-backup", "--category", "history", "--label", safe_label], check=False)

    merge_script = os.path.join(local_bin, "antigravity-merge-history.py")
    if not os.path.isfile(merge_script):
        merge_script = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bin", "antigravity-merge-history.py")

    ts = int(datetime.datetime.now().timestamp())
    if is_ide:
        toggle_ide_history(p_dir, shared_pool, is_shared, ts, merge_script)
    else:
        toggle_app_history(p_dir, shared_pool, is_shared, ts, merge_script)


__all__ = ["safe_toggle_history_mode"]
