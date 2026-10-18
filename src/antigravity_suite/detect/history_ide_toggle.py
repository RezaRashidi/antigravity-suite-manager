"""
Safe history mode toggling for Antigravity IDE instances.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys

from antigravity_suite.detect.constants import GREEN, NC
from antigravity_suite.detect.history_helpers import copy_sqlite_db_safely, get_db_step_count


def toggle_ide_history(p_dir: str, shared_pool: str, is_shared: bool, ts: int, merge_script: str) -> None:
    ide_root = os.path.join(p_dir, ".gemini", "antigravity-ide") if not p_dir.endswith("antigravity-ide") else p_dir
    os.makedirs(ide_root, exist_ok=True)
    ide_conv, ide_brain = os.path.join(ide_root, "conversations"), os.path.join(ide_root, "brain")

    if is_shared:
        if os.path.islink(ide_conv): os.unlink(ide_conv)
        os.makedirs(ide_conv, exist_ok=True)
        copied = 0
        for db in glob.glob(os.path.join(shared_pool, "conversations", "*.db")):
            copy_sqlite_db_safely(db, os.path.join(ide_conv, os.path.basename(db)))
            copied += 1
        if os.path.islink(ide_brain): os.unlink(ide_brain)
        os.makedirs(ide_brain, exist_ok=True)
        for s_name in ["conversation_summaries.db", "conversation_summaries.db-wal", "conversation_summaries.db-shm", "agyhub_summaries_proto.pb"]:
            s_path = os.path.join(ide_root, s_name)
            if os.path.islink(s_path):
                try: os.unlink(s_path)
                except Exception: pass
        for sum_f in glob.glob(os.path.join(shared_pool, "*summaries*")):
            if not sum_f.endswith(("-wal", "-shm")):
                try: copy_sqlite_db_safely(sum_f, os.path.join(ide_root, os.path.basename(sum_f)))
                except Exception: pass
        print(f"{GREEN}[SUCCESS] Antigravity IDE history set to Isolated Private.{NC}")
        print(f"  • Existing {copied} conversations cloned locally to {ide_conv}.")
    else:
        copied = 0
        if os.path.isdir(ide_conv) and not os.path.islink(ide_conv):
            for db in glob.glob(os.path.join(ide_conv, "*.db")):
                dst = os.path.join(shared_pool, "conversations", os.path.basename(db))
                should = not os.path.exists(dst) or get_db_step_count(db) > get_db_step_count(dst) or (
                    get_db_step_count(db) == get_db_step_count(dst) and os.path.getmtime(db) > os.path.getmtime(dst)
                )
                if should:
                    copy_sqlite_db_safely(db, dst)
                    copied += 1
            try: os.rename(ide_conv, f"{ide_conv}.bak_{ts}")
            except Exception: pass
        if os.path.isdir(ide_brain) and not os.path.islink(ide_brain):
            for b in glob.glob(os.path.join(ide_brain, "*")):
                dst_b = os.path.join(shared_pool, "brain", os.path.basename(b))
                if os.path.isdir(b): shutil.copytree(b, dst_b, dirs_exist_ok=True)
                else: shutil.copy2(b, dst_b)
            try: os.rename(ide_brain, f"{ide_brain}.bak_{ts}")
            except Exception: pass
        if not os.path.islink(ide_conv): os.symlink(os.path.join(shared_pool, "conversations"), ide_conv)
        if not os.path.islink(ide_brain): os.symlink(os.path.join(shared_pool, "brain"), ide_brain)
        for s_name in ["conversation_summaries.db", "agyhub_summaries_proto.pb"]:
            s_link = os.path.join(ide_root, s_name)
            if not os.path.islink(s_link):
                if os.path.isfile(s_link):
                    try: os.rename(s_link, f"{s_link}.bak_{ts}")
                    except Exception: pass
                master_s = os.path.join(shared_pool, s_name)
                if os.path.isfile(master_s): os.symlink(master_s, s_link)
        if os.path.isfile(merge_script):
            subprocess.run([sys.executable, merge_script, "--master", shared_pool, "--quiet"], check=False)
        print(f"{GREEN}[SUCCESS] Antigravity IDE history merged and linked to Shared 3-Way Sync.{NC}")
        print(f"  • {copied} private conversations merged into master pool.")
