"""
Automated Backup and Restore Manager Facade for Antigravity History.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from antigravity_suite.history.backup_create import create_pre_merge_backup
from antigravity_suite.history.backup_entry import BackupEntry, get_backup_root, prune_backups
from antigravity_suite.history.backup_restore import list_backups, restore_backup

__all__ = ["BackupEntry", "HistoryBackupManager"]


class HistoryBackupManager:
    """Manages pre-modification backup snapshots, listing, and restoration."""

    @staticmethod
    def get_backup_root(user_home: Optional[Union[str, Path]] = None) -> Path:
        return get_backup_root(user_home)

    @classmethod
    def create_pre_merge_backup(
        cls,
        effective_master: Path,
        candidate_vscdbs: Optional[List[Path]] = None,
        user_home: Optional[Union[str, Path]] = None,
        description: str = "Pre-merge automatic backup",
        max_backups: int = 10,
    ) -> Optional[BackupEntry]:
        return create_pre_merge_backup(effective_master, candidate_vscdbs, user_home, description, max_backups)

    @classmethod
    def list_backups(cls, user_home: Optional[Union[str, Path]] = None) -> List[BackupEntry]:
        return list_backups(user_home)

    @classmethod
    def restore_backup(
        cls,
        backup_id_or_path: str,
        user_home: Optional[Union[str, Path]] = None,
    ) -> bool:
        return restore_backup(backup_id_or_path, user_home)

    @classmethod
    def prune_backups(cls, backup_root: Path, max_keep: int = 10) -> None:
        prune_backups(backup_root, max_keep)
