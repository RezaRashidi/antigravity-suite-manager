"""
Data cleanup and removal operations for Antigravity App, IDE, and shared history.
"""

from __future__ import annotations

import glob
import os
import shutil

from antigravity_suite.migration.cleanup_apps import delete_app_data, delete_ide_data
from antigravity_suite.migration.constants import (
    ANTIGRAVITY_CONF_DIR,
    GEMINI_DIR,
    MASTER_GEMINI,
    REAL_HOME,
    log_info,
    log_success,
)
from antigravity_suite.migration.safety import create_safety_backup

__all__ = [
    "REAL_HOME",
    "delete_all_data",
    "delete_app_data",
    "delete_history_data",
    "delete_ide_data",
]


def delete_history_data(backup: bool = True) -> bool:
    """Removes shared conversation databases, summaries index, and brain artifacts."""
    log_info("Cleaning shared conversation history and brain artifacts...")
    if backup:
        create_safety_backup(category="history", label="pre_delete_history_data")

    cleaned = 0
    for item in ["conversations", "brain", "annotations"]:
        p = os.path.join(MASTER_GEMINI, item)
        if os.path.exists(p):
            shutil.rmtree(p, ignore_errors=True)
            cleaned += 1

    for sum_f in glob.glob(os.path.join(MASTER_GEMINI, "*summaries*")):
        try: os.remove(sum_f); cleaned += 1
        except Exception: pass

    for pb_f in glob.glob(os.path.join(MASTER_GEMINI, "*.pb")):
        try: os.remove(pb_f); cleaned += 1
        except Exception: pass

    os.makedirs(os.path.join(MASTER_GEMINI, "conversations"), exist_ok=True)
    os.makedirs(os.path.join(MASTER_GEMINI, "brain"), exist_ok=True)
    os.makedirs(os.path.join(MASTER_GEMINI, "annotations"), exist_ok=True)

    log_success(f"Conversation history cleaned ({cleaned} items removed).")
    return True


def delete_all_data(backup: bool = True) -> bool:
    """Removes all App, IDE, history, and suite data while preserving safety backups."""
    log_info("Performing full cleanup of all Antigravity suite data...")
    if backup:
        create_safety_backup(category="all", label="pre_delete_all_data")

    delete_app_data(backup=False)
    delete_ide_data(backup=False)
    delete_history_data(backup=False)

    from antigravity_suite.migration import cleanup
    real_home = getattr(cleanup, "REAL_HOME", None) or REAL_HOME

    if os.path.isdir(ANTIGRAVITY_CONF_DIR):
        for item in glob.glob(os.path.join(ANTIGRAVITY_CONF_DIR, "*")):
            if os.path.basename(item) == "backups": continue
            if os.path.isdir(item): shutil.rmtree(item, ignore_errors=True)
            else:
                try: os.remove(item)
                except Exception: pass

    if os.path.isdir(GEMINI_DIR):
        for item in glob.glob(os.path.join(GEMINI_DIR, "*")):
            if os.path.isdir(item): shutil.rmtree(item, ignore_errors=True)
            else:
                try: os.remove(item)
                except Exception: pass

    log_success("All Antigravity suite data has been completely cleaned.")
    return True
