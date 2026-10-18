"""
Safe history mode toggling for Antigravity App clone instances.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys

from antigravity_suite.detect.constants import GREEN, NC
from antigravity_suite.detect.history_helpers import copy_sqlite_db_safely, get_db_step_count


def toggle_app_history(p_dir: str, shared_pool: str, is_shared: bool, ts: int, merge_script: str) -> None:
    target_link = os.path.join(p_dir, ".gemini", "antigravity")
    if is_shared:
        if os.path.islink(target_link):
            os.unlink(target_link)
        iso_conv, iso_brain = os.path.join(target_link, "conversations"), os.path.join(target_link, "brain")
        os.makedirs(iso_conv, exist_ok=True)
        os.makedirs(iso_brain, exist_ok=True)

        copied = 0
        for db in glob.glob(os.path.join(shared_pool, "conversations", "*.db")):
            copy_sqlite_db_safely(db, os.path.join(iso_conv, os.path.basename(db)))
            copied += 1
        for sum_f in glob.glob(os.path.join(shared_pool, "*summaries*")):
            if not sum_f.endswith(("-wal", "-shm")):
                copy_sqlite_db_safely(sum_f, os.path.join(target_link, os.path.basename(sum_f)))
        print(f"{GREEN}[SUCCESS] Clone history set to Isolated Private.{NC}")
        print(f"  • Existing {copied} conversations cloned locally to {iso_conv}.")
    else:
        copied = 0
        if os.path.isdir(target_link) and not os.path.islink(target_link):
            c_conv = os.path.join(target_link, "conversations")
            if os.path.isdir(c_conv):
                for db in glob.glob(os.path.join(c_conv, "*.db")):
                    dst = os.path.join(shared_pool, "conversations", os.path.basename(db))
                    should = not os.path.exists(dst) or get_db_step_count(db) > get_db_step_count(dst) or (
                        get_db_step_count(db) == get_db_step_count(dst) and os.path.getmtime(db) > os.path.getmtime(dst)
                    )
                    if should:
                        copy_sqlite_db_safely(db, dst)
                        copied += 1
            c_brain = os.path.join(target_link, "brain")
            if os.path.isdir(c_brain):
                for b in glob.glob(os.path.join(c_brain, "*")):
                    dst_b = os.path.join(shared_pool, "brain", os.path.basename(b))
                    if os.path.isdir(b): shutil.copytree(b, dst_b, dirs_exist_ok=True)
                    else: shutil.copy2(b, dst_b)
            try: os.rename(target_link, f"{target_link}.bak_{ts}")
            except Exception: pass

        os.makedirs(os.path.dirname(target_link), exist_ok=True)
        if not os.path.islink(target_link):
            os.symlink(shared_pool, target_link)
        if os.path.isfile(merge_script):
            subprocess.run([sys.executable, merge_script, "--master", shared_pool, "--quiet"], check=False)
        print(f"{GREEN}[SUCCESS] Clone history merged and linked to Shared 3-Way Sync.{NC}")
        print(f"  • {copied} private conversations merged into master pool.")
