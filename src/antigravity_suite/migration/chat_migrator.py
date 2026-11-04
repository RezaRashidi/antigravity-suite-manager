"""
One-Shot Legacy Chat Migrator (v2.5.5 -> v2.6.0).

Inspects Antigravity IDE version and migrates legacy chat trajectories
from VS Code state.vscdb into the unified v2.6.0+ SQLite database format.
"""

from __future__ import annotations

import base64
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from antigravity_suite.config import SuiteConfig, get_user_home
from antigravity_suite.detect.inspectors import inspect_ide_dir
from antigravity_suite.history.merger import merge_histories
from antigravity_suite.history.vscdb_sync import discover_candidate_vscdbs
from antigravity_suite.proto.wire_extractor import extract_entries_from_proto


def parse_version_tuple(ver_str: str) -> Tuple[int, ...]:
    nums = re.findall(r"\d+", str(ver_str))
    return tuple(map(int, nums[:3])) if nums else (0, 0, 0)


def check_ide_version(ide_dir: Optional[str] = None) -> Dict[str, Any]:
    cands = [ide_dir] if ide_dir else ["/opt/antigravity-ide", "/opt/antigravity"]
    info = next((inspect_ide_dir(c) for c in cands if c and os.path.isdir(c)), None)
    ver = info.get("version", "Unknown") if info else "Unknown"
    is_v260_plus = parse_version_tuple(ver) >= (2, 6, 0)
    t_path = info.get("path", str(cands[0])) if info else str(cands[0])
    return {"path": t_path, "version": ver, "is_v260_plus": is_v260_plus, "supported": is_v260_plus}


def plan_migration(home: Optional[Path] = None) -> Dict[str, Any]:
    h = Path(home or get_user_home())
    vscdbs = discover_candidate_vscdbs(h)
    legacy_ids: Set[str] = set()
    for vscdb in vscdbs:
        if not vscdb.is_file():
            continue
        try:
            con = sqlite3.connect(vscdb)
            cur = con.cursor()
            for row in cur.execute(
                "SELECT value FROM ItemTable WHERE key IN "
                "('antigravityUnifiedStateSync.trajectorySummaries', 'antigravityUnifiedStateSync');"
            ):
                raw = base64.b64decode(row[0])
                legacy_ids.update(extract_entries_from_proto(raw).keys())
            con.close()
        except Exception:
            pass

    m_db = h / ".gemini" / "antigravity" / "conversation_summaries.db"
    existing_ids: Set[str] = set()
    if m_db.is_file():
        try:
            con = sqlite3.connect(m_db)
            cur = con.cursor()
            for row in cur.execute("SELECT conversation_id FROM conversation_summaries;"):
                existing_ids.add(row[0])
            con.close()
        except Exception:
            pass

    to_migrate = legacy_ids - existing_ids
    return {
        "legacy_total": len(legacy_ids),
        "already_in_v260": len(legacy_ids & existing_ids),
        "to_migrate_count": len(to_migrate),
        "to_migrate_ids": sorted(list(to_migrate)),
        "total_existing_v260": len(existing_ids),
    }


def run_migration(force: bool = False, skip_backup: bool = False, home: Optional[Path] = None) -> Dict[str, Any]:
    h = Path(home or get_user_home())
    ver_info = check_ide_version()
    plan = plan_migration(h)
    stats = merge_histories(quiet=True, force_rebuild=force, user_home=h, skip_backup=skip_backup)
    post_plan = plan_migration(h)
    return {
        "status": "success",
        "ide_version": ver_info["version"],
        "is_v260_plus": ver_info["is_v260_plus"],
        "legacy_found": plan["legacy_total"],
        "previously_migrated": plan["already_in_v260"],
        "newly_migrated": max(0, plan["to_migrate_count"] - post_plan["to_migrate_count"]),
        "total_v260_chats": post_plan["total_existing_v260"],
        "stats": stats.to_dict(),
    }
