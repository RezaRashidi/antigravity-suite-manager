"""
Backup and byte helper utilities for history splicing.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

SOURCE_CID = "8cb6361c-23aa-42c8-be32-b7859e8dc87c"
TARGET_CID = "c99bd561-40b1-47a4-b851-10d371ff1bcd"
CUTOFF_SRC = 2994
CUTOFF_TGT = 31394


def create_splice_backup(home: Path) -> Path:
    """Creates a full timestamped backup of source and target conversations."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = home / ".config" / "antigravity" / "backups" / f"splice_{SOURCE_CID[:8]}_to_{TARGET_CID[:8]}_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    gemini = home / ".gemini" / "antigravity"

    for cid in [SOURCE_CID, TARGET_CID]:
        db = gemini / "conversations" / f"{cid}.db"
        if db.exists():
            shutil.copy2(db, backup_dir / f"{cid}.db")
        brain = gemini / "brain" / cid
        if brain.exists():
            shutil.copytree(brain, backup_dir / "brain" / cid)

    sum_db = gemini / "conversation_summaries.db"
    if sum_db.exists():
        shutil.copy2(sum_db, backup_dir / "conversation_summaries.db")

    print(f"[Backup] Created full safety backup at: {backup_dir}")
    return backup_dir


def fix_cid_bytes(data: bytes | None) -> bytes | None:
    """Replaces source CID with target CID in raw bytes."""
    if not data:
        return data
    return data.replace(SOURCE_CID.encode("utf-8"), TARGET_CID.encode("utf-8"))
