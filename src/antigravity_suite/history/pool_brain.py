"""
Project Brain Folders and Artifact Synchronization.
"""

from __future__ import annotations

import glob
import os
import re
import shutil
from pathlib import Path
from typing import List, Optional, Set

UUID_REGEX = re.compile(r"^[0-9a-fA-F-]{36}$")


def merge_brain_folders(
    brain_pools: List[str],
    master_brain_dir: Path,
    tombstones: Optional[Set[str]] = None,
) -> int:
    """Merges project brain folders and transcripts from external pools into master_brain_dir."""
    brain_folders_merged = 0
    for b_pool in brain_pools:
        if Path(b_pool).resolve() == master_brain_dir.resolve():
            continue
        for b_item in glob.glob(os.path.join(b_pool, "*")):
            if not os.path.isdir(b_item):
                continue
            c_uuid = os.path.basename(b_item)
            if not UUID_REGEX.match(c_uuid) or (tombstones and c_uuid in tombstones):
                continue

            target_brain_item = master_brain_dir / c_uuid
            if not target_brain_item.exists():
                try:
                    shutil.copytree(b_item, target_brain_item, symlinks=True)
                    brain_folders_merged += 1
                except Exception:
                    pass
            elif _brain_needs_update(b_item, target_brain_item):
                _copy_newer_brain_files(b_item, target_brain_item)
    return brain_folders_merged


def _brain_needs_update(src_item: str, tgt_item: Path) -> bool:
    try:
        if os.path.getmtime(src_item) > (tgt_item.stat().st_mtime + 2.0):
            return True
        src_logs = os.path.join(src_item, ".system_generated", "logs")
        tgt_logs = tgt_item / ".system_generated" / "logs"
        if os.path.isdir(src_logs):
            if not tgt_logs.is_dir():
                return True
            for log_name in ("transcript.jsonl", "transcript_full.jsonl"):
                s_f = os.path.join(src_logs, log_name)
                if os.path.isfile(s_f):
                    t_f = tgt_logs / log_name
                    if not t_f.is_file() or os.stat(s_f).st_size > t_f.stat().st_size or os.stat(s_f).st_mtime > (t_f.stat().st_mtime + 2.0):
                        return True
        for entry in os.scandir(src_item):
            if entry.is_file():
                t_f = tgt_item / entry.name
                if not t_f.is_file() or entry.stat().st_size > t_f.stat().st_size or entry.stat().st_mtime > (t_f.stat().st_mtime + 2.0):
                    return True
    except Exception:
        pass
    return False


def _copy_newer_brain_files(src_item: str, tgt_item: Path) -> None:
    for root, _, files in os.walk(src_item):
        target_dir = tgt_item / os.path.relpath(root, src_item)
        target_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            sf, df = os.path.join(root, f), target_dir / f
            if not df.exists() or os.path.getsize(sf) > df.stat().st_size or os.path.getmtime(sf) > (df.stat().st_mtime + 2.0):
                try: shutil.copy2(sf, df)
                except Exception: pass
