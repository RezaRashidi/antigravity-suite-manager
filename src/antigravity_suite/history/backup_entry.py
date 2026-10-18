"""
History Backup Data Models and Root Directory Management.
"""

from __future__ import annotations

import glob
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from antigravity_suite.config import get_user_home


@dataclass
class BackupEntry:
    """Metadata describing a historical backup snapshot."""
    backup_id: str
    timestamp: str
    backup_dir: str
    description: str
    master_app_dir: str
    files: List[str]
    vscdb_entries_count: int


def get_backup_root(user_home: Optional[Union[str, Path]] = None) -> Path:
    """Returns canonical root directory where backups are stored."""
    home = Path(user_home).resolve() if user_home else get_user_home()
    backup_dir = home / ".config" / "antigravity" / "backups" / "history"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def prune_backups(backup_root: Path, max_keep: int = 10) -> None:
    """Prunes oldest backup folders keeping only max_keep most recent snapshots."""
    try:
        dirs = sorted(
            [Path(p) for p in glob.glob(os.path.join(str(backup_root), "*")) if os.path.isdir(p)],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if len(dirs) > max_keep:
            for old_dir in dirs[max_keep:]:
                shutil.rmtree(old_dir, ignore_errors=True)
    except Exception:
        pass
