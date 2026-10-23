#!/usr/bin/env python3
"""
Compacts an oversized Antigravity conversation by archiving older turns
and promoting an authentic compaction checkpoint into the conversation base.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from scripts.compact_backup import create_pre_compact_backup, update_summaries
from scripts.compact_engine import compact_sqlite_db, compact_transcript_file

TARGET_CID = "c99bd561-40b1-47a4-b851-10d371ff1bcd"
BASE_STEP = 33223
LAST_STEP = 33450
TRANSCRIPT_START_LINE = 32581
TRANSCRIPT_END_LINE = 32843


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compact oversized Antigravity conversation")
    parser.add_argument("--cid", type=str, default=TARGET_CID, help="Target conversation ID")
    parser.add_argument("--base-step", type=int, default=BASE_STEP, help="First step index to keep")
    parser.add_argument("--last-step", type=int, default=LAST_STEP, help="Last step index to keep")
    parser.add_argument("--execute", action="store_true", help="Execute live compaction (defaults to dry-run)")
    parser.add_argument("--user-home", type=str, default=str(Path.home()), help="User home directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    home = Path(args.user_home).resolve()
    gemini = home / ".gemini" / "antigravity"
    db_path = gemini / "conversations" / f"{args.cid}.db"
    logs_dir = gemini / "brain" / args.cid / ".system_generated" / "logs"

    print("=" * 60)
    print(f"Antigravity Conversation Compactor ({'EXECUTE' if args.execute else 'DRY RUN'})")
    print(f"Target: {args.cid[:8]} | Keep steps: {args.base_step}..{args.last_step}")
    print("=" * 60)

    if not db_path.exists():
        print(f"[Error] Database {db_path} does not exist.")
        return 1

    if args.execute:
        create_pre_compact_backup(home, args.cid)

    new_count = compact_sqlite_db(db_path, args.base_step, args.last_step, dry_run=not args.execute)
    for log_name in ["transcript.jsonl", "transcript_full.jsonl"]:
        p = logs_dir / log_name
        compact_transcript_file(p, TRANSCRIPT_START_LINE, TRANSCRIPT_END_LINE, args.base_step, dry_run=not args.execute)

    update_summaries(gemini, args.cid, new_count, dry_run=not args.execute)
    if args.execute:
        print("[History Sync] Triggering background synchronization...")
        os.system(f"/home/reza/.local/bin/antigravity-merge-history.py --master {gemini}")
        print(f"[Success] Conversation {args.cid[:8]} successfully compacted to {new_count} steps!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
