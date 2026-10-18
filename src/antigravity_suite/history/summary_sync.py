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
) -> Tuple[sqlite3.Connection, Dict[str, bytes]]:
    """Synchronizes conversation metadata in SQLite conversation_summaries.db and proto dict."""
    home = Path(user_home).resolve() if user_home else get_user_home()
    all_summaries: Dict[str, bytes] = {}

    con = sqlite3.connect(str(master_sum_db), timeout=15.0)
    ensure_summaries_schema(con)
    cur = con.cursor()
    cur.execute("UPDATE conversation_summaries SET source='' WHERE source='CORTEX_TRAJECTORY_SOURCE_CASCADE_CLIENT';")
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
            conv_id=conv_id,
            effective_master=effective_master,
            master_conv_dir=master_conv_dir,
            master_brain_dir=master_brain_dir,
            existing_rows=existing_rows,
            all_summaries=all_summaries,
            cur=cur,
            con=con,
            stats=stats,
            pinned_set=pinned_set,
            project_mappings=project_mappings,
        )

    con.commit()
    return con, all_summaries
