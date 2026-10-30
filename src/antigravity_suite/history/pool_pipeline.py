"""
Pre-Merge Safety Backup, Deletion Sync, and Pool Ingestion Pipeline.

Handles automated transactional backups, tombstones, raw DB merges,
brain folder synchronization, and database reconstitution.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Set, Tuple

from antigravity_suite.history.backup import HistoryBackupManager
from antigravity_suite.history.deletion import detect_and_sync_deletions, get_tombstones
from antigravity_suite.history.models import SyncStats
from antigravity_suite.history.discovery import (
    discover_pinned_conversation_ids,
    replicate_pinned_conversations_order,
    replicate_projects_order,
)
from antigravity_suite.history.pool_merger import merge_brain_folders, merge_raw_db_pools
from antigravity_suite.history.reconstruction import reconstruct_missing_databases
from antigravity_suite.history.subagents import discover_subagent_uuids


def prepare_and_merge_pools(
    effective_master: Path,
    master_conv_dir: Path,
    master_brain_dir: Path,
    conv_pools: List[str],
    brain_pools: List[str],
    candidate_vscdbs: List[str],
    home: Path,
    force_rebuild: bool,
    skip_backup: bool,
    stats: SyncStats,
) -> Tuple[Set[str], Set[str], Set[str]]:
    """Executes backup, deletion synchronization, raw file pool ingestion, and pinned discovery."""
    if not skip_backup:
        backup_entry = HistoryBackupManager.create_pre_merge_backup(
            effective_master=effective_master,
            candidate_vscdbs=candidate_vscdbs,
            user_home=home,
            description="Pre-merge automatic backup",
        )
        if backup_entry:
            stats.backup_id = backup_entry.backup_id

    stats.conversations_deleted = detect_and_sync_deletions(
        effective_master=effective_master,
        candidate_vscdbs=candidate_vscdbs,
        conv_pools=conv_pools,
        brain_pools=brain_pools,
        all_summaries={},
        stats=stats,
        user_home=home,
    )
    tombstones = get_tombstones(effective_master)
    subagents = discover_subagent_uuids(brain_pools + [str(master_brain_dir)])

    stats.db_files_merged = merge_raw_db_pools(conv_pools, master_conv_dir, tombstones=tombstones)
    stats.brain_folders_merged = merge_brain_folders(brain_pools, master_brain_dir, tombstones=tombstones, subagents=subagents)
    stats.databases_reconstructed = reconstruct_missing_databases(
        brain_pools=brain_pools,
        master_brain_dir=master_brain_dir,
        master_conv_dir=master_conv_dir,
        force_rebuild=force_rebuild,
        tombstones=tombstones,
        subagents=subagents,
    )

    pinned_ids = discover_pinned_conversation_ids(user_home=home)
    replicate_pinned_conversations_order(pinned_ids, user_home=home)
    replicate_projects_order(user_home=home)

    return tombstones, pinned_ids, subagents
