"""
Multi-Profile History Replication and Distribution Engine.

Replicates canonical conversation_summaries.db, trajectory databases,
and Protobuf indexes to all target IDE configurations and user profiles.
"""

from __future__ import annotations

import glob
import os
import shutil
import sqlite3
from pathlib import Path
from typing import List

from antigravity_suite.history.sqlite_store import copy_sqlite_db_safely, get_actual_steps_count


def replicate_to_ide_profiles(
    target_ide_dirs: List[str],
    effective_master: Path,
    master_sum_db: Path,
    master_conv_dir: Path,
    master_proto: Path,
    con: sqlite3.Connection,
) -> None:
    """
    Replicates canonical SQLite summaries, conversation databases, and protobuf files
    to all target IDE profile directories using safe SQLite backup API.
    """
    valid_targets = []
    for td in sorted(set(target_ide_dirs)):
        if os.path.isdir(td) and os.path.realpath(td) != str(effective_master):
            if "suite-manager" in os.path.basename(td):
                continue
            valid_targets.append(td)

    for target_d in valid_targets:
        try:
            tgt_conv_dir = os.path.join(target_d, "conversations")
            os.makedirs(tgt_conv_dir, exist_ok=True)

            # 1. Replicate canonical conversation_summaries.db to root of profile
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
                        try:
                            dest_c.close()
                        except Exception:
                            pass

            # 2. Maintain conversation_summaries.db inside conversations/ subfolder (Bug 16)
            # Must strictly symlink to avoid dual-path database desync
            t_sum_db = os.path.join(tgt_conv_dir, "conversation_summaries.db")
            if not os.path.islink(t_sum_db) and not (
                os.path.exists(t_sum_db) and os.path.samefile(str(master_sum_db), t_sum_db)
            ):
                dest_c = None
                try:
                    if os.path.exists(tgt_root_sum_db):
                        if os.path.exists(t_sum_db):
                            try:
                                os.remove(t_sum_db)
                            except Exception:
                                pass
                        try:
                            os.symlink("../conversation_summaries.db", t_sum_db)
                        except Exception:
                            dest_c = sqlite3.connect(t_sum_db, timeout=15.0)
                            con.backup(dest_c)
                    else:
                        dest_c = sqlite3.connect(t_sum_db, timeout=15.0)
                        con.backup(dest_c)
                except Exception:
                    pass
                finally:
                    if dest_c:
                        try:
                            dest_c.close()
                        except Exception:
                            pass

            # 3. Replicate trajectory .db files with strict step precedence
            if not os.path.islink(tgt_conv_dir) and not os.path.samefile(str(master_conv_dir), tgt_conv_dir):
                for db_src in glob.glob(os.path.join(str(master_conv_dir), "*.db")):
                    base_name = os.path.basename(db_src)
                    if base_name == "conversation_summaries.db":
                        continue
                    tgt_db = os.path.join(tgt_conv_dir, base_name)
                    needs_copy = False
                    if not os.path.exists(tgt_db) or os.path.getsize(tgt_db) == 0:
                        needs_copy = True
                    else:
                        src_steps = get_actual_steps_count(db_src)
                        tgt_steps = get_actual_steps_count(tgt_db)
                        if src_steps > tgt_steps:
                            needs_copy = True
                        elif src_steps < tgt_steps:
                            needs_copy = False
                        else:
                            if os.path.getmtime(db_src) > (os.path.getmtime(tgt_db) + 2.0):
                                needs_copy = True

                    if needs_copy:
                        copy_sqlite_db_safely(db_src, tgt_db)

            # 4. Replicate agyhub_summaries_proto.pb
            t_proto = os.path.join(target_d, "agyhub_summaries_proto.pb")
            if master_proto.is_file():
                if not os.path.islink(t_proto) and not (
                    os.path.exists(t_proto) and os.path.samefile(str(master_proto), t_proto)
                ):
                    shutil.copy2(master_proto, t_proto)
        except Exception:
            pass
