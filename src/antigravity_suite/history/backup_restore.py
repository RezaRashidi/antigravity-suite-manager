"""
History Backup Snapshot Listing and Restoration.
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Union

from antigravity_suite.history.backup_entry import BackupEntry, get_backup_root


def list_backups(user_home: Optional[Union[str, Path]] = None) -> List[BackupEntry]:
    """Lists all existing backup entries, sorted from newest to oldest."""
    backup_root = get_backup_root(user_home)
    backups: List[BackupEntry] = []
    for d in sorted(glob.glob(os.path.join(str(backup_root), "*")), reverse=True):
        mf_path = os.path.join(d, "manifest.json")
        if os.path.isdir(d) and os.path.isfile(mf_path):
            try:
                with open(mf_path, "r", encoding="utf-8") as mf:
                    backups.append(BackupEntry(**json.load(mf)))
            except Exception:
                pass
    return backups


def _restore_sqlite_and_files(src_dir: Path, target_master: Path) -> None:
    src_db = src_dir / "conversation_summaries.db"
    if src_db.is_file():
        dest_db = target_master / "conversation_summaries.db"
        try:
            with sqlite3.connect(str(src_db), timeout=15.0) as s, sqlite3.connect(str(dest_db), timeout=15.0) as d:
                s.backup(d)
                d.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        except Exception:
            shutil.copy2(src_db, dest_db)
            for sc in [src_dir / (src_db.name + ext) for ext in ("-wal", "-shm")]:
                if sc.is_file():
                    shutil.copy2(sc, target_master / sc.name)
        sub_link = target_master / "conversations" / "conversation_summaries.db"
        try:
            if sub_link.is_symlink() or not sub_link.exists():
                if sub_link.exists() or sub_link.is_symlink():
                    sub_link.unlink()
                sub_link.symlink_to("../conversation_summaries.db")
        except Exception:
            pass

    src_proto = src_dir / "agyhub_summaries_proto.pb"
    if src_proto.is_file():
        shutil.copy2(src_proto, target_master / "agyhub_summaries_proto.pb")
    src_anno = src_dir / "annotations"
    if src_anno.is_dir():
        dest_anno = target_master / "annotations"
        dest_anno.mkdir(parents=True, exist_ok=True)
        for pbtxt in glob.glob(os.path.join(str(src_anno), "*.pbtxt")):
            shutil.copy2(pbtxt, os.path.join(str(dest_anno), os.path.basename(pbtxt)))


def restore_backup(backup_id_or_path: str, user_home: Optional[Union[str, Path]] = None) -> bool:
    """Restores a backup snapshot given its backup ID or directory path."""
    backup_root = get_backup_root(user_home)
    cand_dir = Path(backup_id_or_path)
    if not cand_dir.is_dir():
        cand_dir = backup_root / backup_id_or_path
    if not (cand_dir.is_dir() and (cand_dir / "manifest.json").is_file()):
        return False
    try:
        with open(cand_dir / "manifest.json", "r", encoding="utf-8") as mf:
            manifest = BackupEntry(**json.load(mf))
        target_master = Path(manifest.master_app_dir)
        target_master.mkdir(parents=True, exist_ok=True)
        _restore_sqlite_and_files(cand_dir, target_master)
        vsc_file = cand_dir / "vscdb_keys.json"
        if vsc_file.is_file():
            with open(vsc_file, "r", encoding="utf-8") as vf:
                vsc_records: Dict[str, Dict[str, Optional[str]]] = json.load(vf)
            for vsc_path, keys in vsc_records.items():
                if os.path.isfile(vsc_path):
                    with sqlite3.connect(vsc_path, timeout=15.0) as v_con:
                        for k, v in keys.items():
                            if v is not None:
                                v_con.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?);", (k, v))
                        v_con.commit()
        src_manifest = cand_dir / "sync_manifest.json"
        if src_manifest.is_file():
            shutil.copy2(src_manifest, target_master / "sync_manifest.json")
        return True
    except Exception:
        return False
