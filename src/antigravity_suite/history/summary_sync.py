"""
Master Summaries Synchronization Coordinator.

Coordinates loading, ingesting, and resolving all conversation entries in SQLite and Proto.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from antigravity_suite.config import get_user_home
from antigravity_suite.history.models import SyncStats
from antigravity_suite.history.projects import discover_project_mappings
from antigravity_suite.history.resolver import collect_all_conversation_ids, resolve_conversation_item
from antigravity_suite.history.sqlite_store import ensure_summaries_schema, load_existing_summaries
from antigravity_suite.proto.wire import extract_entries_from_proto, extract_pure_binary_summary


def synchronize_master_summaries(
    effective_master: Path,
    master_conv_dir: Path,
    master_brain_dir: Path,
    master_sum_db: Path,
    master_proto: Path,
    stats: SyncStats,
    pinned_set: Optional[Set[str]] = None,
    user_home: Optional[Path] = None,
    tombstones: Optional[Set[str]] = None,
    candidate_vscdbs: Optional[List[str]] = None,
    force_rebuild: bool = False,
) -> Tuple[sqlite3.Connection, Dict[str, bytes]]:
    """Synchronizes conversation metadata in SQLite conversation_summaries.db and proto dict."""
    home = Path(user_home).resolve() if user_home else get_user_home()
    all_summaries: Dict[str, bytes] = {}

    con = sqlite3.connect(str(master_sum_db), timeout=15.0)
    ensure_summaries_schema(con)
    cur = con.cursor()
    cur.execute("UPDATE conversation_summaries SET source='' WHERE source='CORTEX_TRAJECTORY_SOURCE_CASCADE_CLIENT';")
    if tombstones:
        cur.executemany("DELETE FROM conversation_summaries WHERE conversation_id = ?;", [(t,) for t in tombstones])
        try: cur.executemany("DELETE FROM conversations_fts WHERE conversation_id = ?;", [(t,) for t in tombstones])
        except Exception: pass
    cur.execute("CREATE TABLE IF NOT EXISTS sync_file_stats (conv_id TEXT PRIMARY KEY, db_mtime REAL, db_size INTEGER, tr_mtime REAL, tr_size INTEGER);")
    cached_stats = {r[0]: (r[1], r[2], r[3], r[4]) for r in cur.execute("SELECT conv_id, db_mtime, db_size, tr_mtime, tr_size FROM sync_file_stats;").fetchall()}
    con.commit()
    existing_rows = load_existing_summaries(master_sum_db)

    # Ingest existing valid summaries from SQLite
    for c_id, row in existing_rows.items():
        if not (tombstones and c_id in tombstones) and row[4]:
            raw = extract_pure_binary_summary(row[4])
            if raw and len(raw) > 20:
                all_summaries[c_id] = raw

    # Ingest master protobuf binary summaries if available
    if master_proto.is_file():
        try:
            with open(master_proto, "rb") as f:
                proto_data = f.read()
            for c_uuid, raw in extract_entries_from_proto(proto_data).items():
                if not (tombstones and c_uuid in tombstones) and raw and len(raw) > 20 and c_uuid not in all_summaries:
                    all_summaries[c_uuid] = raw
        except Exception:
            pass

    if candidate_vscdbs:
        from antigravity_suite.history.vscdb_sync import ingest_vscdb_summaries
        ingest_vscdb_summaries(candidate_vscdbs, all_summaries, master_conv_dir, con, pinned_set=pinned_set, tombstones=tombstones)
        existing_rows = load_existing_summaries(master_sum_db)

    all_conv_ids = collect_all_conversation_ids(
        master_conv_dir=master_conv_dir,
        existing_rows=existing_rows,
        extra_ids=all_summaries.keys(),
        tombstones=tombstones,
        master_brain_dir=master_brain_dir,
    )
    project_mappings = discover_project_mappings(home)

    for conv_id in sorted(all_conv_ids):
        resolve_conversation_item(
            conv_id=conv_id, effective_master=effective_master, master_conv_dir=master_conv_dir,
            master_brain_dir=master_brain_dir, existing_rows=existing_rows, all_summaries=all_summaries,
            cur=cur, con=con, stats=stats, pinned_set=pinned_set, project_mappings=project_mappings,
            force_rebuild=force_rebuild, cached_stats=cached_stats,
        )

    if stats.dirty_conv_ids:
        cur.executemany("INSERT OR REPLACE INTO sync_file_stats VALUES (?, ?, ?, ?, ?);", [(cid, cached_stats[cid][0], cached_stats[cid][1], cached_stats[cid][2], cached_stats[cid][3]) for cid in stats.dirty_conv_ids if cid in cached_stats])

    all_summaries = {cid: raw for cid, raw in all_summaries.items() if cid in all_conv_ids}
    con.commit()
    return con, all_summaries
