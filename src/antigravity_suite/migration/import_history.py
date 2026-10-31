"""
Conversation history import and database step merge operations.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tarfile
from antigravity_suite.migration.constants import LOCAL_BIN, MASTER_GEMINI, log_err, log_info, log_success, log_warn
from antigravity_suite.migration.safety import create_safety_backup
from antigravity_suite.migration.tar_utils import get_db_step_count, safe_extract_tar


def trigger_history_merge() -> None:
    """Runs antigravity-merge-history.py to update indexes and IDE state."""
    if not MASTER_GEMINI or not os.path.exists(MASTER_GEMINI) or "/tmp" in os.path.realpath(str(MASTER_GEMINI)):
        return
    if os.environ.get("ANTIGRAVITY_TEST_MODE") == "1" or os.environ.get("ANTIGRAVITY_SKIP_SAFETY_BACKUP") == "1":
        return

    from antigravity_suite.detect.constants import get_bin_script
    merge_script = get_bin_script("antigravity-merge-history.py")

    if os.path.isfile(merge_script):
        try:
            subprocess.run([sys.executable, merge_script, "--master", MASTER_GEMINI, "--quiet"], check=False)
        except Exception as e:
            log_warn(f"Merge history trigger returned: {e}")


def import_history(archive_path: str | None = None, extracted_dir: str | None = None) -> bool:
    """Imports and merges conversation history from an archive into the master pool."""
    if not extracted_dir and (not archive_path or not os.path.isfile(archive_path)):
        log_err(f"Archive file not found: {archive_path}")
        return False

    log_info(f"Importing conversation history from {archive_path or extracted_dir}...")
    create_safety_backup(category="history", label="pre_import")

    master_conv, master_brain, master_anno = (os.path.join(MASTER_GEMINI, x) for x in ["conversations", "brain", "annotations"])
    for d in [master_conv, master_brain, master_anno]: os.makedirs(d, exist_ok=True)
    imported_dbs, imported_brains = 0, 0

    import contextlib, tempfile

    @contextlib.contextmanager
    def _res():
        if extracted_dir: yield extracted_dir
        else:
            with tempfile.TemporaryDirectory() as tmp:
                with tarfile.open(archive_path, "r:*") as tar: safe_extract_tar(tar, path=tmp)
                yield tmp

    with _res() as tmpdir:
        src_conv = os.path.join(tmpdir, "conversations") if os.path.isdir(os.path.join(tmpdir, "conversations")) else os.path.join(tmpdir, "history", "conversations")
        if os.path.isdir(src_conv):
            for db in glob.glob(os.path.join(src_conv, "*.db")):
                dst = os.path.join(master_conv, os.path.basename(db))
                copy_ok = not os.path.exists(dst) or (get_db_step_count(db) > get_db_step_count(dst)) or (get_db_step_count(db) == get_db_step_count(dst) and os.path.getmtime(db) > os.path.getmtime(dst))
                if copy_ok:
                    shutil.copy2(db, dst)
                    for ext in ["-wal", "-shm"]:
                        if os.path.exists(f"{db}{ext}"): shutil.copy2(f"{db}{ext}", f"{dst}{ext}")
                        elif os.path.exists(f"{dst}{ext}"):
                            try: os.remove(f"{dst}{ext}")
                            except Exception: pass
                    imported_dbs += 1

        src_brain = os.path.join(tmpdir, "brain") if os.path.isdir(os.path.join(tmpdir, "brain")) else os.path.join(tmpdir, "history", "brain")
        if os.path.isdir(src_brain):
            for item in glob.glob(os.path.join(src_brain, "*")):
                dst_b = os.path.join(master_brain, os.path.basename(item))
                if os.path.isdir(item): shutil.copytree(item, dst_b, dirs_exist_ok=True)
                else: shutil.copy2(item, dst_b)
                imported_brains += 1

        src_anno = os.path.join(tmpdir, "annotations") if os.path.isdir(os.path.join(tmpdir, "annotations")) else os.path.join(tmpdir, "history", "annotations")
        if os.path.isdir(src_anno):
            for a in glob.glob(os.path.join(src_anno, "*")):
                dst_a = os.path.join(master_anno, os.path.basename(a))
                if not os.path.exists(dst_a): shutil.copy2(a, dst_a)

    log_info(f"Ingested {imported_dbs} conversations and {imported_brains} brain folders.")
    trigger_history_merge()
    log_success(f"History import complete! Master shared pool now has {len(glob.glob(os.path.join(master_conv, '*.db')))} total conversations.")
    return True
