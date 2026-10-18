"""
Backup restoration engine across history and suite configurations.
"""

from __future__ import annotations

import glob
import os
import sys
import tarfile
import tempfile
from antigravity_suite.migration.constants import log_err, log_info, log_success
from antigravity_suite.migration.import_history import trigger_history_merge
from antigravity_suite.migration.restore_handlers import restore_history_files, restore_suite_files
from antigravity_suite.migration.safety import create_safety_backup
from antigravity_suite.migration.tar_utils import safe_extract_tar


def restore_backup(backup_path: str) -> bool:
    """Restores full or partial suite state from a backup tarball."""
    if not os.path.isfile(backup_path):
        log_err(f"Backup file not found: {backup_path}")
        return False

    fn = os.path.basename(backup_path)
    log_info(f"Inspecting backup: {fn}...")
    mod = sys.modules.get("antigravity-migration")
    safety_fn = getattr(mod, "create_safety_backup", create_safety_backup) if mod else create_safety_backup
    safety_fn(category="all", label="pre_restore_snapshot")

    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(backup_path, "r:*") as tar:
            safe_extract_tar(tar, path=tmpdir)

        hist_dir = os.path.join(tmpdir, "history")
        if not os.path.isdir(hist_dir) and (os.path.isdir(os.path.join(tmpdir, "conversations")) or glob.glob(os.path.join(tmpdir, "*summaries*"))):
            hist_dir = tmpdir

        if os.path.isdir(hist_dir):
            restore_history_files(hist_dir)
            trigger_fn = getattr(mod, "trigger_history_merge", trigger_history_merge) if mod else trigger_history_merge
            trigger_fn()

        suite_dir = os.path.join(tmpdir, "suite")
        if not os.path.isdir(suite_dir) and (os.path.isfile(os.path.join(tmpdir, "GEMINI.md")) or os.path.isdir(os.path.join(tmpdir, "config"))):
            suite_dir = tmpdir

        if os.path.isdir(suite_dir):
            restore_suite_files(suite_dir)

    log_success(f"Restore from {fn} completed successfully!")
    return True
