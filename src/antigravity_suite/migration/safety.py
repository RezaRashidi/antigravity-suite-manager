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
    AGENTS_DIR,
    ANTIGRAVITY_CONF_DIR,
    BACKUPS_DIR,
    BOLD,
    CONFIG_DIR,
    CYAN,
    GEMINI_DIR,
    MASTER_GEMINI,
    NC,
    REAL_HOME,
    YELLOW,
    log_info,
    log_success,
)
from antigravity_suite.migration.tar_utils import format_size, get_timestamp


def create_safety_backup(category: str = "history", label: str = "pre_change") -> Optional[str]:
    """Creates a timestamped gzip safety backup tarball before destructive operations."""
    if not MASTER_GEMINI or not os.path.exists(MASTER_GEMINI): return None
    if os.environ.get("ANTIGRAVITY_TEST_MODE") == "1" or os.environ.get("ANTIGRAVITY_SKIP_SAFETY_BACKUP") == "1": return None

    cat_dir = os.path.join(BACKUPS_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)
    tar_name = f"{category}-{label}-{get_timestamp()}.tar.gz"
    tar_path = os.path.join(cat_dir, tar_name)
    log_info(f"Creating safety snapshot in {tar_path}...")

    with tarfile.open(tar_path, "w:gz") as tar:
        if category in ["history", "all"]:
            for item in ["conversations", "brain", "annotations"]:
                p = os.path.join(MASTER_GEMINI, item)
                if os.path.exists(p): tar.add(p, arcname=os.path.join("history", item), recursive=True)
            for sum_f in glob.glob(os.path.join(MASTER_GEMINI, "*summaries*")):
                if os.path.isfile(sum_f): tar.add(sum_f, arcname=os.path.join("history", os.path.basename(sum_f)))
            for bak in ["conversations.bak", "brain.bak"]:
                p = os.path.join(GEMINI_DIR, "antigravity-ide", bak)
                if os.path.isdir(p): tar.add(p, arcname=f"history/ide_{bak}", recursive=True)

        if category in ["suite", "configs", "all"]:
            if os.path.isfile(os.path.join(GEMINI_DIR, "GEMINI.md")):
                tar.add(os.path.join(GEMINI_DIR, "GEMINI.md"), arcname="suite/GEMINI.md")
            if os.path.isdir(CONFIG_DIR): tar.add(CONFIG_DIR, arcname="suite/config", recursive=True)
            if os.path.isdir(AGENTS_DIR): tar.add(AGENTS_DIR, arcname="suite/agents", recursive=True)
            if os.path.isdir(os.path.join(MASTER_GEMINI, "mcp")):
                tar.add(os.path.join(MASTER_GEMINI, "mcp"), arcname="suite/mcp", recursive=True)
            if os.path.isdir(ANTIGRAVITY_CONF_DIR):
                for conf_f in glob.glob(os.path.join(ANTIGRAVITY_CONF_DIR, "*.conf")):
                    tar.add(conf_f, arcname=os.path.join("suite", "config_antigravity", os.path.basename(conf_f)))
                if os.path.isdir(os.path.join(ANTIGRAVITY_CONF_DIR, "accounts")):
                    tar.add(os.path.join(ANTIGRAVITY_CONF_DIR, "accounts"), arcname="suite/accounts", recursive=True)
            token_targets = [
                (os.path.join(GEMINI_DIR, "jetski-standalone-oauth-token"), "gemini-token"),
                (os.path.join(REAL_HOME, ".antigravity-profile2", ".gemini", "jetski-standalone-oauth-token"), "acc2-token"),
                (os.path.join(REAL_HOME, ".gemini-ide", "jetski-standalone-oauth-token"), "gemini-ide-token"),
                (os.path.join(REAL_HOME, ".gemide", "jetski-standalone-oauth-token"), "gemide-token"),
            ]
            for t_path, t_arc in token_targets:
                if os.path.isfile(t_path): tar.add(t_path, arcname=os.path.join("suite", "tokens", t_arc))

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
