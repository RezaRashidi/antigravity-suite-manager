"""
High-level Push and Pull synchronization orchestrator.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, Tuple

from antigravity_suite.cloud.constants import ANNOTATIONS_DIR, BRAIN_DIR, CONVERSATIONS_DIR
from antigravity_suite.cloud.pull_ingest import ingest_staged_conversations
from antigravity_suite.cloud.rclone_client import (
    is_rclone_installed,
    is_remote_configured,
    rclone_check_remote_alive,
    rclone_copy_dir,
)
from antigravity_suite.cloud.sqlite_wal import flush_all_wal


def execute_cloud_push(remote: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Flushes SQLite WAL journals and copies conversation state to cloud remote."""
    if not is_rclone_installed():
        return False, "rclone binary is not installed.", {}
    if not is_remote_configured(remote):
        return False, f"Remote '{remote}' is not configured in rclone.", {}

    wal_flushed = flush_all_wal(CONVERSATIONS_DIR)
    rem_target = f"{remote.strip().rstrip(':')}:"

    rc1, err1 = rclone_copy_dir(CONVERSATIONS_DIR, f"{rem_target}conversations")
    if rc1 != 0:
        return False, f"Failed copying conversations: {err1}", {}

    rc2, err2 = rclone_copy_dir(BRAIN_DIR, f"{rem_target}brain")
    if rc2 != 0:
        return False, f"Failed copying brain artifacts: {err2}", {}

    if os.path.isdir(ANNOTATIONS_DIR):
        rclone_copy_dir(ANNOTATIONS_DIR, f"{rem_target}annotations")

    stats = {"wal_flushed": wal_flushed, "remote": remote}
    return True, f"Successfully pushed conversations and artifacts to {remote}.", stats


def execute_cloud_pull(remote: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Pulls cloud changes to staging, resolves conflicts, provisions workspaces, and merges."""
    if not is_rclone_installed():
        return False, "rclone binary is not installed.", {}
    if not is_remote_configured(remote):
        return False, f"Remote '{remote}' is not configured in rclone.", {}
    if not rclone_check_remote_alive(remote):
        return False, f"Cannot connect to remote '{remote}'. Please check network.", {}

    rem_target = f"{remote.strip().rstrip(':')}:"
    with tempfile.TemporaryDirectory(prefix="antigravity_cloud_stage_") as stage_dir:
        rc1, err1 = rclone_copy_dir(f"{rem_target}conversations", os.path.join(stage_dir, "conversations"))
        if rc1 != 0:
            return False, f"Failed downloading conversations: {err1}", {}

        rclone_copy_dir(f"{rem_target}brain", os.path.join(stage_dir, "brain"))
        rclone_copy_dir(f"{rem_target}annotations", os.path.join(stage_dir, "annotations"))

        ingest_stats = ingest_staged_conversations(stage_dir)
        return True, "Successfully pulled and merged cloud changes.", ingest_stats
