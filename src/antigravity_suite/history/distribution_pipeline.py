"""
Master History Distribution and Store Finalization Pipeline.

Handles vscdb enrichment, hub-partitioned proto serialization,
multi-profile replication, and annotation synchronization.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Set

from antigravity_suite.history.annotation_sync import sync_annotation_files
from antigravity_suite.history.discovery import replicate_projects_order
from antigravity_suite.history.distribution import replicate_to_ide_profiles
from antigravity_suite.history.models import SyncStats
from antigravity_suite.history.proto_sync import serialize_master_proto
from antigravity_suite.history.vscdb_sync import ingest_vscdb_summaries, write_vscdb_unified_state


def finalize_and_distribute_history(
    con: sqlite3.Connection,
    all_summaries: Dict[str, bytes],
    candidate_vscdbs: List[str],
    ide_candidates: List[str],
    effective_master: Path,
    master_sum_db: Path,
    master_conv_dir: Path,
    master_proto: Path,
    pinned_ids: Set[str],
    tombstones: Set[str],
    force_rebuild: bool,
    stats: SyncStats,
    user_home: Optional[Path] = None,
) -> None:
    """Enriches state.vscdb, serializes Hub proto, replicates profiles, and writes annotations."""
    try:
        cur = con.cursor()
        stats.ide_state_ingested = ingest_vscdb_summaries(
            candidate_vscdbs=candidate_vscdbs,
            all_summaries=all_summaries,
            master_conv_dir=master_conv_dir,
            con=con,
            pinned_set=pinned_ids,
            tombstones=tombstones,
        )

        serialize_master_proto(master_proto, all_summaries)

        write_vscdb_unified_state(candidate_vscdbs, all_summaries)
        replicate_projects_order(user_home=user_home)

        try:
            cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            con.commit()
        except Exception:
            pass

        replicate_to_ide_profiles(
            target_ide_dirs=ide_candidates,
            effective_master=effective_master,
            master_sum_db=master_sum_db,
            master_conv_dir=master_conv_dir,
            master_proto=master_proto,
            con=con,
        )

        target_annos = None if force_rebuild else stats.dirty_conv_ids
        sync_annotation_files(effective_master, cur, pinned_set=pinned_ids, target_conv_ids=target_annos)

        stats.total_active_history = cur.execute("SELECT count(*) FROM conversation_summaries;").fetchone()[0]

        try:
            cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            con.commit()
        except Exception:
            pass
    finally:
        con.close()
