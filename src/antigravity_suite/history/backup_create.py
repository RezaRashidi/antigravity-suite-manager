"""
History Pre-Merge Snapshot Creation.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import shutil
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Union

from antigravity_suite.history.backup_entry import BackupEntry, get_backup_root, prune_backups


def _backup_sqlite(master_db: Path, snapshot_dir: Path) -> List[str]:
    if not master_db.is_file():
        return []
    dest_db = snapshot_dir / "conversation_summaries.db"
    try:
        with sqlite3.connect(str(master_db), timeout=15.0) as s, sqlite3.connect(str(dest_db), timeout=15.0) as d:
            s.backup(d)
    except Exception:
        shutil.copy2(master_db, dest_db)
        for sc in [master_db.parent / (master_db.name + ext) for ext in ("-wal", "-shm")]:
            if sc.is_file():
                shutil.copy2(sc, snapshot_dir / sc.name)
    return ["conversation_summaries.db"]


def _backup_vscdbs(vscdbs: List[Path], snapshot_dir: Path) -> int:
    vscdb_data: Dict[str, Dict[str, Optional[str]]] = {}
    for vsc_path in vscdbs:
        if vsc_path.is_file():
            try:
                with sqlite3.connect(str(vsc_path), timeout=15.0) as con:
                    rows = con.execute("SELECT key, value FROM ItemTable WHERE key LIKE 'antigravityUnifiedStateSync%';").fetchall()
                    if rows:
                        vscdb_data[str(vsc_path)] = {r[0]: r[1] for r in rows}
            except Exception:
                pass
    if vscdb_data:
        with open(snapshot_dir / "vscdb_keys.json", "w", encoding="utf-8") as vf:
            json.dump(vscdb_data, vf, indent=2)
    return len(vscdb_data)


def create_pre_merge_backup(
    effective_master: Path,
    candidate_vscdbs: Optional[List[Path]] = None,
    user_home: Optional[Union[str, Path]] = None,
    description: str = "Pre-merge automatic backup",
    max_backups: int = 10,
) -> Optional[BackupEntry]:
    """Creates a timestamped snapshot before history merging."""
    try:
        backup_root = get_backup_root(user_home)
        now = datetime.datetime.now(datetime.timezone.utc)
        snap_dir = backup_root / f"{now.strftime('%Y%m%d_%H%M%S_%f')[:19]}_pre_merge"
        snap_dir.mkdir(parents=True, exist_ok=True)
        files = _backup_sqlite(effective_master / "conversation_summaries.db", snap_dir)

        proto = effective_master / "agyhub_summaries_proto.pb"
        if proto.is_file():
            shutil.copy2(proto, snap_dir / "agyhub_summaries_proto.pb")
            files.append("agyhub_summaries_proto.pb")

        anno_dir = effective_master / "annotations"
        if anno_dir.is_dir():
            dest_anno = snap_dir / "annotations"
            dest_anno.mkdir(parents=True, exist_ok=True)
            for pbtxt in glob.glob(os.path.join(str(anno_dir), "*.pbtxt")):
                shutil.copy2(pbtxt, os.path.join(str(dest_anno), os.path.basename(pbtxt)))
            files.append("annotations")

        vsc_count = _backup_vscdbs(candidate_vscdbs or [], snap_dir)
        if vsc_count > 0:
            files.append("vscdb_keys.json")

        manifest_f = effective_master / "sync_manifest.json"
        if manifest_f.is_file():
            shutil.copy2(manifest_f, snap_dir / "sync_manifest.json")
            files.append("sync_manifest.json")

        entry = BackupEntry(snap_dir.name, now.isoformat(), str(snap_dir), description, str(effective_master), files, vsc_count)
        with open(snap_dir / "manifest.json", "w", encoding="utf-8") as mf:
            json.dump(asdict(entry), mf, indent=2)
        prune_backups(backup_root, max_keep=max_backups)
        return entry
    except Exception:
        return None
