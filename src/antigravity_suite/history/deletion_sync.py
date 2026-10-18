"""
Asymmetric deletion detection and synchronization engine.
"""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set

from antigravity_suite.history.deletion_manifest import load_manifest, save_manifest
from antigravity_suite.history.deletion_purge import purge_conversation
from antigravity_suite.history.deletion_vscdb import get_active_ide_ids
from antigravity_suite.history.models import SyncStats


def _find_ghost_ids(current_app_ids: Set[str], tombstones: Set[str], effective_master: Path, conv_pools: List[str], brain_pools: List[str]) -> Set[str]:
    ghosts: Set[str] = set()
    all_conv = [effective_master / "conversations"] + [Path(p) for p in conv_pools]
    all_brain = [effective_master / "brain"] + [Path(p) for p in brain_pools]
    for c_id in current_app_ids:
        if c_id not in tombstones:
            if not any((d / f"{c_id}.db").is_file() for d in all_conv):
                if not any((b / c_id / ".system_generated" / "logs" / "transcript.jsonl").is_file() for b in all_brain):
                    ghosts.add(c_id)
    return ghosts


def detect_and_sync_deletions(
    effective_master: Path, candidate_vscdbs: List[Path], conv_pools: List[str], brain_pools: List[str],
    all_summaries: Dict[str, bytes], stats: SyncStats, con: Optional[sqlite3.Connection] = None,
    user_home: Optional[Path] = None,
) -> int:
    """Detects asymmetric deletions between Desktop App and IDE, purging deleted chats."""
    own_conn = False
    if con is None:
        db_path = effective_master / "conversation_summaries.db"
        if not db_path.is_file():
            return 0
        con, own_conn = sqlite3.connect(str(db_path), timeout=15.0), True

    try:
        cur = con.cursor()
        app_rows = cur.execute("SELECT conversation_id FROM conversation_summaries WHERE killed = 0;").fetchall()
        cur_app = set(r[0] for r in app_rows if r[0])
        cur_ide = get_active_ide_ids(candidate_vscdbs)
        manifest = load_manifest(effective_master)
        prev_app = set(manifest.get("known_app_ids", manifest.get("known_ids", [])))
        prev_ide = set(manifest.get("known_ide_ids", manifest.get("known_ids", [])))
        tombstones = set(manifest.get("tombstones", {}).keys())

        if not prev_app and not prev_ide:
            manifest["known_app_ids"] = sorted(list(cur_app - tombstones))
            manifest["known_ide_ids"] = sorted(list(cur_ide - tombstones))
            manifest["known_ids"] = sorted(list((cur_app | cur_ide) - tombstones))
            save_manifest(effective_master, manifest)
            return 0

        del_app = set() if (not cur_app or (len(prev_app) > 5 and len(cur_app) < len(prev_app) * 0.5)) else ((prev_app - cur_app) - tombstones)
        del_ide = set() if (not candidate_vscdbs or not cur_ide or (len(prev_ide) > 5 and len(cur_ide) < len(prev_ide) * 0.5)) else ((prev_ide - cur_ide) - tombstones)
        all_conv = [effective_master / "conversations"] + [Path(p) for p in conv_pools]
        del_ide = {c for c in del_ide if not any((d / f"{c}.db").is_file() and (d / f"{c}.db").stat().st_size > 100 for d in all_conv)}
        ghost_ids = _find_ghost_ids(cur_app, tombstones, effective_master, conv_pools, brain_pools)
        to_purge = del_app | del_ide | ghost_ids

        if not to_purge:
            manifest["known_app_ids"], manifest["known_ide_ids"] = sorted(list(cur_app - tombstones)), sorted(list(cur_ide - tombstones))
            manifest["known_ids"] = sorted(list((cur_app | cur_ide) - tombstones))
            save_manifest(effective_master, manifest)
            return 0

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for c_id in sorted(to_purge):
            src = "app" if c_id in del_app else ("ide" if c_id in del_ide else "ghost")
            purge_conversation(c_id, effective_master, con, candidate_vscdbs, conv_pools, brain_pools, all_summaries, user_home=user_home)
            manifest.setdefault("tombstones", {})[c_id] = {"deleted_at": now_iso, "source": src}
            stats.conversations_deleted += 1
            stats.dirty_conv_ids.add(c_id)

        manifest["known_app_ids"] = sorted(list((cur_app - to_purge) - tombstones))
        manifest["known_ide_ids"] = sorted(list((cur_ide - to_purge) - tombstones))
        manifest["known_ids"] = sorted(list(((cur_app | cur_ide) - to_purge) - tombstones))
        save_manifest(effective_master, manifest)
        return len(to_purge)
    finally:
        if own_conn and con:
            try:
                con.close()
            except Exception:
                pass
