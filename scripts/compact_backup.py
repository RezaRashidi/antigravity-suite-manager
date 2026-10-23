"""
Backup and summary synchronization for conversation compactor.
"""

from __future__ import annotations

import datetime
import shutil
import sqlite3
from pathlib import Path


def create_pre_compact_backup(home: Path, cid: str) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = home / ".config" / "antigravity" / "backups" / f"compact_{cid[:8]}_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    gemini = home / ".gemini" / "antigravity"
    conv_dir, brain_dir = gemini / "conversations", gemini / "brain" / cid

    for ext in ["db", "db-wal", "db-shm"]:
        p = conv_dir / f"{cid}.{ext}"
        if p.exists(): shutil.copy2(p, backup_dir / f"{cid}.{ext}")

    sum_db = gemini / "conversation_summaries.db"
    if sum_db.exists(): shutil.copy2(sum_db, backup_dir / "conversation_summaries.db")

    if brain_dir.exists():
        dst_brain = backup_dir / "brain" / cid
        dst_brain.mkdir(parents=True, exist_ok=True)
        logs_dir = brain_dir / ".system_generated" / "logs"
        if logs_dir.exists():
            dst_logs = dst_brain / ".system_generated" / "logs"
            dst_logs.mkdir(parents=True, exist_ok=True)
            for f in logs_dir.glob("*.jsonl"): shutil.copy2(f, dst_logs / f.name)

    print(f"[Backup] Full pre-compact snapshot created at {backup_dir}")
    return backup_dir


def update_summaries(gemini_dir: Path, cid: str, step_count: int, dry_run: bool = True) -> None:
    sum_db = gemini_dir / "conversation_summaries.db"
    if not sum_db.exists(): return
    con = sqlite3.connect(sum_db)
    cur = con.cursor()
    row = cur.execute("SELECT step_count FROM conversation_summaries WHERE conversation_id = ?;", (cid,)).fetchone()
    old_steps = row[0] if row else 0
    print(f"[Summaries] step_count: {old_steps} -> {step_count}")
    if not dry_run:
        cur.execute("UPDATE conversation_summaries SET step_count = ? WHERE conversation_id = ?;", (step_count, cid))
        con.commit()
    con.close()
