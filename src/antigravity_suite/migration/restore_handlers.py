"""
History and Suite sub-handlers for backup restoration.
"""

from __future__ import annotations

import glob
import os
import shutil

from antigravity_suite.migration.constants import (
    AGENTS_DIR,
    ANTIGRAVITY_CONF_DIR,
    CONFIG_DIR,
    REAL_HOME,
    get_gemini_dir,
    get_master_gemini,
    log_info,
    log_success,
)
from antigravity_suite.migration.restore_apps import restore_app_files, restore_ide_files

__all__ = [
    "restore_app_files",
    "restore_history_files",
    "restore_ide_files",
    "restore_suite_files",
]


def restore_history_files(hist_dir: str) -> None:
    """Restores conversation databases, brain artifacts, and annotations from extracted snapshot."""
    log_info("Restoring conversation history, annotations, and brain artifacts...")
    master_gemini = get_master_gemini()
    src_conv, dst_conv = os.path.join(hist_dir, "conversations"), os.path.join(master_gemini, "conversations")
    os.makedirs(dst_conv, exist_ok=True)
    if os.path.isdir(src_conv):
        snap_dbs = {os.path.basename(db) for db in glob.glob(os.path.join(src_conv, "*.db"))}
        for cur_db in glob.glob(os.path.join(dst_conv, "*.db")):
            if os.path.basename(cur_db) not in snap_dbs:
                try:
                    os.remove(cur_db)
                    for ext in ["-wal", "-shm"]:
                        if os.path.exists(f"{cur_db}{ext}"): os.remove(f"{cur_db}{ext}")
                except Exception: pass

        for db in glob.glob(os.path.join(src_conv, "*.db")):
            dst_db = os.path.join(dst_conv, os.path.basename(db))
            shutil.copy2(db, dst_db)
            for ext in ["-wal", "-shm"]:
                s_wal, d_wal = f"{db}{ext}", f"{dst_db}{ext}"
                if os.path.exists(s_wal): shutil.copy2(s_wal, d_wal)
                elif os.path.exists(d_wal):
                    try: os.remove(d_wal)
                    except Exception: pass

    for sub in ["brain", "annotations"]:
        src_sub, dst_sub = os.path.join(hist_dir, sub), os.path.join(master_gemini, sub)
        os.makedirs(dst_sub, exist_ok=True)
        if os.path.isdir(src_sub):
            for item in glob.glob(os.path.join(src_sub, "*")):
                d = os.path.join(dst_sub, os.path.basename(item))
                if os.path.isdir(item): shutil.copytree(item, d, dirs_exist_ok=True)
                else: shutil.copy2(item, d)

    for sum_f in glob.glob(os.path.join(hist_dir, "*summaries*")):
        shutil.copy2(sum_f, os.path.join(master_gemini, os.path.basename(sum_f)))


def restore_suite_files(suite_dir: str) -> None:
    """Restores suite configurations, global rules, agents, skills, and OAuth tokens."""
    log_info("Restoring suite configurations, rules, skills, and accounts...")
    gemini_dir, master_gemini = get_gemini_dir(), get_master_gemini()
    if os.path.isfile(os.path.join(suite_dir, "GEMINI.md")):
        shutil.copy2(os.path.join(suite_dir, "GEMINI.md"), os.path.join(gemini_dir, "GEMINI.md"))
    for sub, dst in [("config", CONFIG_DIR), ("agents", AGENTS_DIR), ("mcp", os.path.join(master_gemini, "mcp"))]:
        if os.path.isdir(os.path.join(suite_dir, sub)): shutil.copytree(os.path.join(suite_dir, sub), dst, dirs_exist_ok=True)
    if os.path.isdir(os.path.join(suite_dir, "accounts")):
        os.makedirs(os.path.join(ANTIGRAVITY_CONF_DIR, "accounts"), exist_ok=True)
        shutil.copytree(os.path.join(suite_dir, "accounts"), os.path.join(ANTIGRAVITY_CONF_DIR, "accounts"), dirs_exist_ok=True)
    if os.path.isdir(os.path.join(suite_dir, "config_antigravity")):
        for cf in glob.glob(os.path.join(suite_dir, "config_antigravity", "*.conf")):
            shutil.copy2(cf, os.path.join(ANTIGRAVITY_CONF_DIR, os.path.basename(cf)))

    tokens_src = os.path.join(suite_dir, "tokens")
    if os.path.isdir(tokens_src):
        for sn, dp in [
            ("gemini-token", os.path.join(gemini_dir, "jetski-standalone-oauth-token")),
            ("acc2-token", os.path.join(REAL_HOME, ".antigravity-profile2", ".gemini", "jetski-standalone-oauth-token")),
            ("gemini-ide-token", os.path.join(REAL_HOME, ".gemini-ide", "jetski-standalone-oauth-token")),
            ("gemide-token", os.path.join(REAL_HOME, ".gemide", "jetski-standalone-oauth-token")),
        ]:
            if os.path.isfile(os.path.join(tokens_src, sn)):
                os.makedirs(os.path.dirname(dp), exist_ok=True)
                shutil.copy2(os.path.join(tokens_src, sn), dp)
                try: os.chmod(dp, 0o600)
                except Exception: pass
                log_success(f"Restored OAuth token to {dp}")
