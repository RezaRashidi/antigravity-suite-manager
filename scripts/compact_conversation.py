#!/usr/bin/env python3
"""
Compacts an oversized Antigravity conversation by archiving older turns
and promoting an authentic compaction checkpoint into the conversation base.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

TARGET_CID = "c99bd561-40b1-47a4-b851-10d371ff1bcd"
BASE_STEP = 33223
LAST_STEP = 33450
TRANSCRIPT_START_LINE = 32581
TRANSCRIPT_END_LINE = 32843  # inclusive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compact oversized Antigravity conversation")
    parser.add_argument("--cid", type=str, default=TARGET_CID, help="Target conversation ID")
    parser.add_argument("--base-step", type=int, default=BASE_STEP, help="First step index to keep")
    parser.add_argument("--last-step", type=int, default=LAST_STEP, help="Last step index to keep")
    parser.add_argument("--execute", action="store_true", help="Execute live compaction (defaults to dry-run)")
    parser.add_argument("--user-home", type=str, default=str(Path.home()), help="User home directory")
    return parser.parse_args()


def create_pre_compact_backup(home: Path, cid: str) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = home / ".config" / "antigravity" / "backups" / f"compact_{cid[:8]}_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    gemini = home / ".gemini" / "antigravity"
    conv_dir = gemini / "conversations"
    brain_dir = gemini / "brain" / cid

    # Backup sqlite files
    for ext in ["db", "db-wal", "db-shm"]:
        p = conv_dir / f"{cid}.{ext}"
        if p.exists():
            shutil.copy2(p, backup_dir / f"{cid}.{ext}")

    # Backup summaries
    sum_db = gemini / "conversation_summaries.db"
    if sum_db.exists():
        shutil.copy2(sum_db, backup_dir / "conversation_summaries.db")

    # Backup brain logs
    if brain_dir.exists():
        dst_brain = backup_dir / "brain" / cid
        dst_brain.mkdir(parents=True, exist_ok=True)
        logs_dir = brain_dir / ".system_generated" / "logs"
        if logs_dir.exists():
            dst_logs = dst_brain / ".system_generated" / "logs"
            dst_logs.mkdir(parents=True, exist_ok=True)
            for f in logs_dir.glob("*.jsonl"):
                shutil.copy2(f, dst_logs / f.name)

    print(f"[Backup] Full pre-compact snapshot created at {backup_dir}")
    return backup_dir


def compact_sqlite_db(db_path: Path, base_step: int, last_step: int, dry_run: bool = True) -> int:
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    total_before = cur.execute("SELECT count(*) FROM steps;").fetchone()[0]
    kept_steps = cur.execute(
        "SELECT idx, step_type, status, has_subtrajectory, metadata, error_details, permissions, task_details, render_info, step_payload, step_format "
        "FROM steps WHERE idx >= ? AND idx <= ? ORDER BY idx ASC;",
        (base_step, last_step),
    ).fetchall()

    new_count = len(kept_steps)
    print(f"[SQLite] Total steps before: {total_before} | Kept steps: {new_count} (range {base_step}..{last_step})")

    if dry_run:
        con.close()
        return new_count

    # Archive copy in conversations folder
    archive_db = db_path.with_name(f"{db_path.stem}.full_archive.db")
    if not archive_db.exists():
        shutil.copy2(db_path, archive_db)
        print(f"[SQLite] Full original database archived to {archive_db}")

    # Re-populate steps table with shifted indices starting at 0
    cur.execute("DELETE FROM steps;")
    for row in kept_steps:
        old_idx = row[0]
        new_idx = old_idx - base_step
        cur.execute(
            "INSERT INTO steps (idx, step_type, status, has_subtrajectory, metadata, error_details, permissions, task_details, render_info, step_payload, step_format) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (new_idx, row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]),
        )

    # Clean auxiliary tables
    cur.execute("DELETE FROM gen_metadata WHERE idx > ?;", (new_count,))
    cur.execute("DELETE FROM executor_metadata WHERE idx > ?;", (new_count,))
    cur.execute("DELETE FROM parent_references WHERE idx > ?;", (new_count,))

    con.commit()
    con.execute("VACUUM;")
    con.close()
    print(f"[SQLite] Compacted database down to {new_count} steps and VACUUM completed.")
    return new_count


def compact_transcript_file(
    file_path: Path, start_line: int, end_line: int, base_step: int, dry_run: bool = True
) -> int:
    if not file_path.exists():
        return 0

    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
        all_lines = fp.readlines()

    total_lines = len(all_lines)
    selected_lines = all_lines[start_line : end_line + 1]
    print(f"[Transcript] {file_path.name}: {total_lines} total lines -> keeping {len(selected_lines)} lines ({start_line}..{end_line})")

    if dry_run:
        return len(selected_lines)

    # Archive full transcript
    archive_file = file_path.with_name(f"{file_path.stem}_full_archive{file_path.suffix}")
    if not archive_file.exists():
        shutil.copy2(file_path, archive_file)
        print(f"[Transcript] Archived {file_path.name} to {archive_file.name}")

    compacted_lines = []
    current_idx = 0
    for line in selected_lines:
        line_str = line.strip()
        if not line_str:
            continue
        try:
            data = json.loads(line_str)
            old_idx = data.get("step_index")
            if old_idx is not None and old_idx >= base_step:
                data["step_index"] = old_idx - base_step
            else:
                data["step_index"] = current_idx
            compacted_lines.append(json.dumps(data, ensure_ascii=False) + "\n")
            current_idx += 1
        except Exception:
            compacted_lines.append(line)
            current_idx += 1

    with open(file_path, "w", encoding="utf-8") as fp:
        fp.writelines(compacted_lines)

    print(f"[Transcript] Wrote {len(compacted_lines)} compacted lines to {file_path.name}")
    return len(compacted_lines)


def update_summaries(gemini_dir: Path, cid: str, step_count: int, dry_run: bool = True) -> None:
    sum_db = gemini_dir / "conversation_summaries.db"
    if not sum_db.exists():
        return

    con = sqlite3.connect(sum_db)
    cur = con.cursor()
    row = cur.execute("SELECT step_count FROM conversation_summaries WHERE conversation_id = ?;", (cid,)).fetchone()
    old_steps = row[0] if row else 0
    print(f"[Summaries] step_count: {old_steps} -> {step_count}")

    if not dry_run:
        cur.execute("UPDATE conversation_summaries SET step_count = ? WHERE conversation_id = ?;", (step_count, cid))
        con.commit()
    con.close()


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
