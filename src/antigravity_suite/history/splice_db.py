"""
SQLite database step migration and index shifting utilities for history splicing.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from antigravity_suite.history.splice_backup import CUTOFF_SRC, CUTOFF_TGT, SOURCE_CID, fix_cid_bytes


def migrate_sqlite_tables(src_db: Path, tgt_db: Path, dry_run: bool = True) -> int:
    """Migrates leaked steps from source DB to target DB and shifts subsequent steps."""
    con_src, con_tgt = sqlite3.connect(src_db), sqlite3.connect(tgt_db)
    step_rows = con_src.execute("SELECT * FROM steps WHERE idx >= ? ORDER BY idx ASC;", (CUTOFF_SRC,)).fetchall()
    shift = len(step_rows)
    if not step_rows:
        print(f"[SQLite] No steps >= {CUTOFF_SRC} found in {SOURCE_CID[:8]}. Already migrated!")
        con_src.close()
        con_tgt.close()
        return 0

    print(f"[SQLite] Found {shift} steps in source DB {SOURCE_CID[:8]} (idx {CUTOFF_SRC}..{step_rows[-1][0]})")
    if dry_run:
        con_src.close()
        con_tgt.close()
        return shift

    gen_rows = con_src.execute("SELECT * FROM gen_metadata WHERE idx >= ? ORDER BY idx ASC;", (CUTOFF_SRC,)).fetchall()
    exec_rows = con_src.execute("SELECT * FROM executor_metadata WHERE idx >= ? ORDER BY idx ASC;", (CUTOFF_SRC,)).fetchall()
    parent_rows = con_src.execute("SELECT * FROM parent_references WHERE idx >= ? ORDER BY idx ASC;", (CUTOFF_SRC,)).fetchall()

    temp_offset = shift + 10000000
    for table in ["steps", "gen_metadata", "executor_metadata", "parent_references"]:
        con_tgt.execute(f"UPDATE {table} SET idx = idx + {temp_offset} WHERE idx > {CUTOFF_TGT};")
        con_tgt.execute(f"UPDATE {table} SET idx = idx - 10000000 WHERE idx > 10000000;")
    con_tgt.commit()

    for r in step_rows:
        new_idx = (CUTOFF_TGT + 1) + (r[0] - CUTOFF_SRC)
        con_tgt.execute(
            """INSERT INTO steps (idx, step_type, status, has_subtrajectory, metadata, error_details, permissions, task_details, render_info, step_payload, step_format)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            (new_idx, r[1], r[2], r[3], fix_cid_bytes(r[4]), r[5], r[6], r[7], r[8], fix_cid_bytes(r[9]), r[10]),
        )
    for r in gen_rows:
        con_tgt.execute("INSERT INTO gen_metadata (idx, data, size) VALUES (?, ?, ?);",
                        ((CUTOFF_TGT + 1) + (r[0] - CUTOFF_SRC), fix_cid_bytes(r[1]), r[2]))
    for r in exec_rows:
        con_tgt.execute("INSERT INTO executor_metadata (idx, data) VALUES (?, ?);",
                        ((CUTOFF_TGT + 1) + (r[0] - CUTOFF_SRC), fix_cid_bytes(r[1])))
    for r in parent_rows:
        con_tgt.execute("INSERT INTO parent_references (idx, data) VALUES (?, ?);",
                        ((CUTOFF_TGT + 1) + (r[0] - CUTOFF_SRC), fix_cid_bytes(r[1])))

    for table in ["steps", "gen_metadata", "executor_metadata", "parent_references"]:
        con_src.execute(f"DELETE FROM {table} WHERE idx >= {CUTOFF_SRC};")

    con_src.commit()
    con_tgt.commit()
    con_src.close()
    con_tgt.close()
    print(f"[SQLite] Successfully migrated {shift} steps and updated indices in target DB.")
    return shift
