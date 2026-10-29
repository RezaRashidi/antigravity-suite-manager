#!/usr/bin/env python3
"""
Splice and Migrate Leaked Session Steps Between Antigravity Conversations.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

from antigravity_suite.history.splice_backup import CUTOFF_SRC, CUTOFF_TGT, SOURCE_CID, TARGET_CID, create_splice_backup
from antigravity_suite.history.splice_db import migrate_sqlite_tables
from antigravity_suite.history.splice_transcript import migrate_tasks, migrate_transcript_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Splice leaked conversation steps")
    parser.add_argument("--execute", action="store_true", help="Execute changes live (defaults to dry-run)")
    parser.add_argument("--user-home", type=str, default=str(Path.home()), help="User home directory")
    return parser.parse_args()


def update_master_summaries(gemini_dir: Path, shift: int, dry_run: bool = True) -> None:
    sum_db = gemini_dir / "conversation_summaries.db"
    if not sum_db.exists():
        return
    con = sqlite3.connect(sum_db)
    r_src = con.execute("SELECT step_count FROM conversation_summaries WHERE conversation_id = ?;", (SOURCE_CID,)).fetchone()
    r_tgt = con.execute("SELECT step_count FROM conversation_summaries WHERE conversation_id = ?;", (TARGET_CID,)).fetchone()
    new_src_steps = CUTOFF_SRC
    new_tgt_steps = (r_tgt[0] if r_tgt else 0) + shift
    print(f"[Summaries] Source steps: {r_src[0] if r_src else 0} -> {new_src_steps} | Target: {r_tgt[0] if r_tgt else 0} -> {new_tgt_steps}")
    if not dry_run:
        con.execute("UPDATE conversation_summaries SET step_count = ?, last_modified_time = ? WHERE conversation_id = ?;",
                    (new_src_steps, "2026-10-21 11:38:24.000000+00:00", SOURCE_CID))
        con.execute("UPDATE conversation_summaries SET step_count = ? WHERE conversation_id = ?;", (new_tgt_steps, TARGET_CID))
        con.commit()
    con.close()


def main() -> int:
    args = parse_args()
    home = Path(args.user_home).resolve()
    gemini = home / ".gemini" / "antigravity"
    src_db, tgt_db = gemini / "conversations" / f"{SOURCE_CID}.db", gemini / "conversations" / f"{TARGET_CID}.db"
    src_brain, tgt_brain = gemini / "brain" / SOURCE_CID, gemini / "brain" / TARGET_CID

    print("=" * 60)
    print(f"Antigravity Leaked Session Splicer ({'EXECUTE' if args.execute else 'DRY RUN'})")
    print(f"Source: {SOURCE_CID[:8]} (>= {CUTOFF_SRC}) -> Target: {TARGET_CID[:8]} (after {CUTOFF_TGT})")
    print("=" * 60)

    if args.execute:
        create_splice_backup(home)

    shift = migrate_sqlite_tables(src_db, tgt_db, dry_run=not args.execute)
    for log_name in ["transcript.jsonl", "transcript_full.jsonl"]:
        migrate_transcript_file(src_brain / ".system_generated" / "logs" / log_name,
                                tgt_brain / ".system_generated" / "logs" / log_name, shift, dry_run=not args.execute)

    migrate_tasks(src_brain, tgt_brain, dry_run=not args.execute)
    update_master_summaries(gemini, shift, dry_run=not args.execute)

    if args.execute:
        print("[History Sync] Triggering background synchronization...")
        merge_cmd = os.path.expanduser("~/.local/bin/antigravity-merge-history.py")
        os.system(f"python3 {merge_cmd} --master {gemini}")
        print("[Complete] All leaked turns successfully spliced into target conversation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
