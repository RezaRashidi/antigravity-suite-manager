"""
Trajectory SQLite Database Replication Utilities.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

from antigravity_suite.history.sqlite_store import copy_sqlite_db_safely, get_actual_steps_count


def replicate_trajectory_dbs(master_conv_dir: Path, tgt_conv_dir: str) -> None:
    """Replicates trajectory .db files with strict step precedence."""
    for db_src in glob.glob(os.path.join(str(master_conv_dir), "*.db")):
        base_name = os.path.basename(db_src)
        if base_name == "conversation_summaries.db":
            continue
        tgt_db = os.path.join(tgt_conv_dir, base_name)
        if not os.path.exists(tgt_db) or os.path.getsize(tgt_db) == 0:
            copy_sqlite_db_safely(db_src, tgt_db)
            continue

        src_stat, tgt_stat = os.stat(db_src), os.stat(tgt_db)
        if src_stat.st_size == tgt_stat.st_size and abs(src_stat.st_mtime - tgt_stat.st_mtime) < 1.0:
            continue

        src_steps = get_actual_steps_count(db_src)
        tgt_steps = get_actual_steps_count(tgt_db)
        if src_steps > tgt_steps or (src_steps == tgt_steps and src_stat.st_mtime > tgt_stat.st_mtime + 2.0):
            copy_sqlite_db_safely(db_src, tgt_db)
