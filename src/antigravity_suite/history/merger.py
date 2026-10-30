"""
Antigravity History Synchronization and Multi-Profile Merge Coordinator.

Orchestrates 3-way synchronization across Antigravity Hub, Antigravity IDE,
and multi-account isolated profiles with safety backups, audit logs, and isolation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

from antigravity_suite.auth import refresh_ide_oauth_token
from antigravity_suite.config import SuiteConfig, get_user_home
from antigravity_suite.history.annotation_sync import sync_annotation_files
from antigravity_suite.history.audit import get_audit_logger
from antigravity_suite.history.collector import (
    collect_all_conversation_ids,
    get_db_trajectory_meta,
    setup_master_directories,
)
from antigravity_suite.history.discovery import discover_all_history_sources
from antigravity_suite.history.distribution_pipeline import finalize_and_distribute_history
from antigravity_suite.history.models import SyncStats
from antigravity_suite.history.pool_pipeline import prepare_and_merge_pools
from antigravity_suite.history.projects import (
    ensure_project_configs,
    get_project_id_for_workspace,
    normalize_workspace_uri,
)
from antigravity_suite.history.proto_sync import serialize_master_proto
from antigravity_suite.history.resolver import resolve_conversation_item
from antigravity_suite.history.summary_sync import synchronize_master_summaries
from antigravity_suite.history.transcript_info import get_transcript_timestamps
from antigravity_suite.history.vscdb_sync import discover_candidate_vscdbs

__all__ = [
    "collect_all_conversation_ids",
    "ensure_project_configs",
    "get_db_trajectory_meta",
    "get_project_id_for_workspace",
    "get_transcript_timestamps",
    "merge_histories",
    "normalize_workspace_uri",
    "resolve_conversation_item",
    "serialize_master_proto",
    "setup_master_directories",
    "sync_annotation_files",
    "synchronize_master_summaries",
]


def merge_histories(
    master_gemini: Optional[Union[str, Path]] = None,
    source_dir: Optional[Union[str, Path]] = None,
    target_dir: Optional[Union[str, Path]] = None,
    quiet: bool = False,
    force_rebuild: bool = False,
    user_home: Optional[Union[str, Path]] = None,
    skip_backup: bool = False,
) -> SyncStats:
    """Executes full synchronization between Hub, IDE, and isolated profiles."""
    home = Path(user_home).resolve() if user_home else get_user_home()
    default_master = home / ".gemini" / "antigravity"
    effective_master = Path(master_gemini or os.environ.get("ANTIGRAVITY_DATA_DIR") or default_master).resolve()

    audit = get_audit_logger(effective_master / "history_merger_audit.log")
    audit.log_event("SYNC_START", {"master": str(effective_master), "home": str(home), "force": force_rebuild})

    ensure_project_configs(user_home=home)
    m_conv_dir, m_brain_dir, m_sum_db, m_proto, _ = setup_master_directories(effective_master)

    stats = SyncStats()
    conv_pools, brain_pools, ide_candidates = discover_all_history_sources(target_dir, home, source_dir)
    candidate_vscdbs = discover_candidate_vscdbs(home, ide_candidates)
    stats.conv_stores_scanned, stats.brain_stores_scanned = len(conv_pools), len(brain_pools)

    tombstones, pinned_ids, subagents = prepare_and_merge_pools(
        effective_master, m_conv_dir, m_brain_dir, conv_pools, brain_pools,
        candidate_vscdbs, home, force_rebuild, skip_backup, stats
    )

    con, all_summaries = synchronize_master_summaries(
        effective_master, m_conv_dir, m_brain_dir, m_sum_db, m_proto, stats, pinned_ids, home, tombstones, candidate_vscdbs, force_rebuild, subagents=subagents
    )

    finalize_and_distribute_history(
        con, all_summaries, candidate_vscdbs, ide_candidates, effective_master,
        m_sum_db, m_conv_dir, m_proto, pinned_ids, tombstones, force_rebuild, stats,
        user_home=home,
    )

    for ide_dir in SuiteConfig(user_home=home).ide_dirs:
        refresh_ide_oauth_token(ide_dir, home)

    audit.log_run_summary(stats.to_dict())
    return stats
