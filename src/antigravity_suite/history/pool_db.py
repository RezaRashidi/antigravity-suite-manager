"""
Raw SQLite Database and Proto Pool Synchronization.
"""

from __future__ import annotations

import glob
import os
import shutil
from pathlib import Path
from typing import List, Optional, Set

from antigravity_suite.history.sqlite_store import copy_sqlite_db_safely, get_actual_steps_count


def merge_raw_db_pools(
    conv_pools: List[str],
    master_conv_dir: Path,
    tombstones: Optional[Set[str]] = None,
) -> int:
    """Merges raw .db and .pb files from external conversation pools into master_conv_dir."""
    db_files_merged = 0
    for pool in conv_pools:
        if Path(pool).resolve() == master_conv_dir.resolve():
            continue
        for src_file in glob.glob(os.path.join(pool, "*")):
            base = os.path.basename(src_file)
            if not (base.endswith(".db") or base.endswith(".pb")) or base == "conversation_summaries.db":
                continue
            cid = base.split(".")[0]
            if tombstones and cid in tombstones:
                continue

            target_file = master_conv_dir / base
            if _should_copy_pool_file(src_file, target_file, base):
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


def _should_copy_pool_file(src_file: str, target_file: Path, base: str) -> bool:
    if not target_file.exists():
        return True
    if target_file.stat().st_size == 0 and os.path.getsize(src_file) > 0:
        return True
    if base.endswith(".db"):
        src_stat, tgt_stat = os.stat(src_file), target_file.stat()
        if src_stat.st_size == tgt_stat.st_size and abs(src_stat.st_mtime - tgt_stat.st_mtime) < 1.0:
            return False
        src_steps = get_actual_steps_count(src_file)
        tgt_steps = get_actual_steps_count(target_file)
        if src_steps > tgt_steps:
            return True
        elif src_steps < tgt_steps:
            return False
        return src_stat.st_mtime > (tgt_stat.st_mtime + 2.0)
    else:
        return os.path.getsize(src_file) > target_file.stat().st_size or os.path.getmtime(src_file) > (target_file.stat().st_mtime + 2.0)
