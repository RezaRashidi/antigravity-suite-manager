"""
Multi-Profile History Replication and Distribution Engine.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path
from typing import List

from antigravity_suite.history.distribution_dbs import replicate_trajectory_dbs


def replicate_to_ide_profiles(
    target_ide_dirs: List[str],
    effective_master: Path,
    master_sum_db: Path,
    master_conv_dir: Path,
    master_proto: Path,
    con: sqlite3.Connection,
) -> None:
    """Replicates canonical SQLite summaries, conversation databases, and protobuf files."""
    valid_targets = [
        td for td in sorted(set(target_ide_dirs))
        if os.path.isdir(td) and Path(td).resolve() != effective_master.resolve() and "suite-manager" not in os.path.basename(td)
    ]

    for target_d in valid_targets:
        try:
            tgt_conv_dir = os.path.join(target_d, "conversations")
            os.makedirs(tgt_conv_dir, exist_ok=True)

            _replicate_summary_db(target_d, master_sum_db, con)

            t_sum_db = os.path.join(tgt_conv_dir, "conversation_summaries.db")
            if os.path.islink(t_sum_db) or os.path.exists(t_sum_db):
                try: os.remove(t_sum_db)
                except Exception: pass

            if not os.path.islink(tgt_conv_dir) and not os.path.samefile(str(master_conv_dir), tgt_conv_dir):
                replicate_trajectory_dbs(master_conv_dir, tgt_conv_dir)

            _replicate_protobuf_files(target_d, master_proto)
        except Exception:
            pass


def _replicate_summary_db(target_d: str, master_sum_db: Path, con: sqlite3.Connection) -> None:
    tgt_root_sum_db = os.path.join(target_d, "conversation_summaries.db")
    if not os.path.islink(tgt_root_sum_db) and not (
        os.path.exists(tgt_root_sum_db) and os.path.samefile(str(master_sum_db), tgt_root_sum_db)
    ):
        dest_c = None
        try:
            dest_c = sqlite3.connect(tgt_root_sum_db, timeout=15.0)
            con.backup(dest_c)
        except Exception:
            pass
        finally:
            if dest_c:
                try: dest_c.close()
                except Exception: pass


def _replicate_protobuf_files(target_d: str, master_proto: Path) -> None:
    if not master_proto.is_file():
        return
    for pb_name in ["agyhub_summaries_proto.pb", "jetbox_summaries.pb", "jetbox_summaries_proto.pb", "agyhub_summaries.pb"]:
        t_pb = os.path.join(target_d, pb_name)
        if os.path.exists(t_pb) or pb_name == "agyhub_summaries_proto.pb":
            if not os.path.islink(t_pb) and not (os.path.exists(t_pb) and os.path.samefile(str(master_proto), t_pb)):
                shutil.copy2(master_proto, t_pb)
