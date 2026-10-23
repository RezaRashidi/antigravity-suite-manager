"""
Safety backup snapshots and listing operations.
"""

from __future__ import annotations

import datetime
import glob
import os
import tarfile
from typing import List, Optional

from antigravity_suite.migration.constants import (
    BACKUPS_DIR,
    BOLD,
    CYAN,
    MASTER_GEMINI,
    NC,
    REAL_HOME,
    YELLOW,
    log_info,
    log_success,
)
from antigravity_suite.migration.safety_collector import populate_safety_tar
from antigravity_suite.migration.tar_utils import format_size, get_timestamp

__all__ = ["REAL_HOME", "create_safety_backup", "list_all_backups"]


def create_safety_backup(category: str = "history", label: str = "pre_change") -> Optional[str]:
    """Creates a timestamped gzip safety backup tarball before destructive operations."""
    if os.environ.get("ANTIGRAVITY_TEST_MODE") == "1" or os.environ.get("ANTIGRAVITY_SKIP_SAFETY_BACKUP") == "1":
        return None
    if category == "history" and (not MASTER_GEMINI or not os.path.exists(MASTER_GEMINI)):
        return None

    cat_dir = os.path.join(BACKUPS_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)
    tar_name = f"{category}-{label}-{get_timestamp()}.tar.gz"
    tar_path = os.path.join(cat_dir, tar_name)
    log_info(f"Creating safety snapshot in {tar_path}...")

    with tarfile.open(tar_path, "w:gz") as tar:
        populate_safety_tar(tar, category)

    log_success(f"Safety snapshot created: {tar_name} ({format_size(os.path.getsize(tar_path))})")
    return tar_path


def list_all_backups() -> List[str]:
    """Lists all available safety backups with dates and sizes."""
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    all_files = sorted(glob.glob(os.path.join(BACKUPS_DIR, "**", "*.tar.gz"), recursive=True), key=os.path.getmtime, reverse=True)
    if not all_files:
        print(f"{YELLOW}No backups found in {BACKUPS_DIR}.{NC}")
        return []
    print(f"\n{CYAN}{'='*88}{NC}\n{BOLD}{CYAN}{'Available Antigravity Backups & Snapshots':^88}{NC}\n{CYAN}{'='*88}{NC}")
    print(f" {'#':<3} {'Filename':<48} {'Size':<10} Created Date\n{'-'*88}")
    for idx, f in enumerate(all_files, 1):
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M:%S")
        print(f" [{idx:<2}] {os.path.basename(f):<48} {format_size(os.path.getsize(f)):<10} {mt}")
    print(f"{CYAN}{'='*88}{NC}")
    return all_files
