"""
Transcript and task log splicing utilities.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from antigravity_suite.history.splice_backup import CUTOFF_SRC, CUTOFF_TGT, SOURCE_CID, TARGET_CID


def migrate_transcript_file(src_path: Path, tgt_path: Path, shift: int, dry_run: bool = True) -> None:
    """Migrates transcript lines from source to target with offset adjustment."""
    if not src_path.exists() or not tgt_path.exists():
        return
    src_lines_migrate, src_lines_keep = [], []
    with open(src_path, "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            idx = d.get("step_index")
            if idx is not None and idx >= CUTOFF_SRC:
                d["step_index"] = (CUTOFF_TGT + 1) + (idx - CUTOFF_SRC)
                src_lines_migrate.append(json.dumps(d, ensure_ascii=False).replace(SOURCE_CID, TARGET_CID) + "\n")
            else:
                src_lines_keep.append(line)

    tgt_lines_before, tgt_lines_after = [], []
    with open(tgt_path, "r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            idx = d.get("step_index")
            if idx is not None and idx > CUTOFF_TGT:
                d["step_index"] = idx + shift
                tgt_lines_after.append(json.dumps(d, ensure_ascii=False) + "\n")
            else:
                tgt_lines_before.append(line)

    print(f"[Transcript] {src_path.name}: Keep {len(src_lines_keep)} src, migrate {len(src_lines_migrate)}, shift {len(tgt_lines_after)} tgt.")
    if dry_run:
        return
    with open(tgt_path, "w", encoding="utf-8") as f:
        f.writelines(tgt_lines_before)
        f.writelines(src_lines_migrate)
        f.writelines(tgt_lines_after)
    with open(src_path, "w", encoding="utf-8") as f:
        f.writelines(src_lines_keep)


def migrate_tasks(src_brain: Path, tgt_brain: Path, dry_run: bool = True) -> None:
    """Moves leaked background task logs from source brain to target brain."""
    src_tasks, tgt_tasks = src_brain / ".system_generated" / "tasks", tgt_brain / ".system_generated" / "tasks"
    tgt_tasks.mkdir(parents=True, exist_ok=True)
    if not src_tasks.exists():
        return
    migrated = 0
    for tf in src_tasks.glob("task-*.log"):
        if tf.stat().st_mtime >= 1792590000:
            if not dry_run:
                shutil.copy2(tf, tgt_tasks / tf.name)
                tf.unlink()
            migrated += 1
    print(f"[Tasks] Migrated {migrated} task logs from source to target.")
