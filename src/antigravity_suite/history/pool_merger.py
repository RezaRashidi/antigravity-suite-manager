"""
Pool Synchronization Engine for Conversation Databases and Brain Folders.

Safely merges raw .db and .pb conversation files and project brain directories
between isolated profiles and the master repository.
"""

from __future__ import annotations

import glob
import os
import re
import shutil
from pathlib import Path
from typing import List, Union

from antigravity_suite.history.sqlite_store import copy_sqlite_db_safely, get_actual_steps_count


def merge_raw_db_pools(conv_pools: List[str], master_conv_dir: Path) -> int:
    """
    Merges raw .db and .pb files from external conversation pools into master_conv_dir.
    Updates files if destination is missing, has fewer steps, or is older.
    Strictly prioritizes step counts for SQLite databases to prevent truncated copies
    from overwriting complete conversations.
    Returns:
        Number of databases successfully merged or updated.
    """
    db_files_merged = 0
    for pool in conv_pools:
        if Path(pool).resolve() == master_conv_dir.resolve():
            continue
        for src_file in glob.glob(os.path.join(pool, "*")):
            base = os.path.basename(src_file)
            if not (base.endswith(".db") or base.endswith(".pb")):
                continue
            if base == "conversation_summaries.db":
                continue

            target_file = master_conv_dir / base
            needs_copy = False
            if not target_file.exists():
                needs_copy = True
            elif target_file.stat().st_size == 0 and os.path.getsize(src_file) > 0:
                needs_copy = True
            elif base.endswith(".db"):
                # STRICT STEP PRECEDENCE (Bug 2 & 10):
                # A truncated database must NEVER overwrite a complete database
                # Fast path: identical size and timestamp means file is already synced
                src_stat = os.stat(src_file)
                tgt_stat = target_file.stat()
                if src_stat.st_size == tgt_stat.st_size and abs(src_stat.st_mtime - tgt_stat.st_mtime) < 1.0:
                    needs_copy = False
                else:
                    src_steps = get_actual_steps_count(src_file)
                    tgt_steps = get_actual_steps_count(target_file)
                    if src_steps > tgt_steps:
                        needs_copy = True
                    elif src_steps < tgt_steps:
                        needs_copy = False
                    else:
                        # Same number of steps: update only if source is genuinely newer
                        if src_stat.st_mtime > (tgt_stat.st_mtime + 2.0):
                            needs_copy = True
            else:
                # Non-sqlite files (.pb)
                if os.path.getsize(src_file) > target_file.stat().st_size:
                    needs_copy = True
                elif os.path.getmtime(src_file) > (target_file.stat().st_mtime + 2.0):
                    needs_copy = True

            if needs_copy:
                if base.endswith(".db"):
                    if copy_sqlite_db_safely(src_file, target_file):
                        db_files_merged += 1
                else:
                    try:
                        shutil.copy2(src_file, target_file)
                        db_files_merged += 1
                    except Exception:
                        pass
    return db_files_merged


def merge_brain_folders(brain_pools: List[str], master_brain_dir: Path) -> int:
    """
    Merges project brain folders and transcripts from external pools into master_brain_dir.
    Recursively updates newer/larger files (e.g. transcript.jsonl and markdown artifacts)
    in existing folders.
    Returns:
        Number of new brain folders imported.
    """
    brain_folders_merged = 0
    for b_pool in brain_pools:
        if Path(b_pool).resolve() == master_brain_dir.resolve():
            continue
        for b_item in glob.glob(os.path.join(b_pool, "*")):
            if not os.path.isdir(b_item):
                continue
            c_uuid = os.path.basename(b_item)
            if not re.match(r"^[0-9a-fA-F-]{36}$", c_uuid):
                continue

            target_brain_item = master_brain_dir / c_uuid
            if not target_brain_item.exists():
                try:
                    shutil.copytree(b_item, target_brain_item, symlinks=True)
                    brain_folders_merged += 1
                except Exception:
                    pass
            else:
                # Update newer or larger files in existing folder
                for root, _, files in os.walk(b_item):
                    rel = os.path.relpath(root, b_item)
                    target_dir = target_brain_item / rel
                    target_dir.mkdir(parents=True, exist_ok=True)
                    for f in files:
                        src_f = os.path.join(root, f)
                        dst_f = target_dir / f
                        if (
                            not dst_f.exists()
                            or os.path.getsize(src_f) > dst_f.stat().st_size
                            or os.path.getmtime(src_f) > (dst_f.stat().st_mtime + 2.0)
                        ):
                            try:
                                shutil.copy2(src_f, dst_f)
                            except Exception:
                                pass
    return brain_folders_merged
