"""
Automated Backup and Restore Manager for Antigravity History.

Creates transactional snapshots of conversation summaries, protobuf indexes,
annotations, and IDE global storage state before modifications, with full rollback
and restore capabilities.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

from antigravity_suite.config import get_user_home


@dataclass
class BackupEntry:
    """Metadata describing a historical backup snapshot."""
    backup_id: str
    timestamp: str
    backup_dir: str
    description: str
    master_app_dir: str
    files: List[str]
    vscdb_entries_count: int


class HistoryBackupManager:
    """Manages pre-modification backup snapshots, listing, and restoration."""

    @staticmethod
    def get_backup_root(user_home: Optional[Union[str, Path]] = None) -> Path:
        """Returns the canonical root directory where backups are stored."""
        home = Path(user_home).resolve() if user_home else get_user_home()
        backup_dir = home / ".config" / "antigravity" / "backups" / "history"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    @classmethod
    def create_pre_merge_backup(
        cls,
        effective_master: Path,
        candidate_vscdbs: Optional[List[Path]] = None,
        user_home: Optional[Union[str, Path]] = None,
        description: str = "Pre-merge automatic backup",
        max_backups: int = 10,
    ) -> Optional[BackupEntry]:
        """
        Creates a timestamped snapshot of conversation_summaries.db,
        agyhub_summaries_proto.pb, annotations, and state.vscdb keys.
        """
        try:
            backup_root = cls.get_backup_root(user_home)
            now = datetime.datetime.now(datetime.timezone.utc)
            timestamp_str = now.strftime("%Y%m%d_%H%M%S_%f")[:19]
            backup_id = f"{timestamp_str}_pre_merge"
            snapshot_dir = backup_root / backup_id
            snapshot_dir.mkdir(parents=True, exist_ok=True)

            backed_up_files: List[str] = []

            # 1. Backup conversation_summaries.db using SQLite backup API for WAL safety
            master_db = effective_master / "conversation_summaries.db"
            if master_db.is_file():
                dest_db = snapshot_dir / "conversation_summaries.db"
                s_con = None
                d_con = None
                try:
                    s_con = sqlite3.connect(str(master_db), timeout=15.0)
                    d_con = sqlite3.connect(str(dest_db), timeout=15.0)
                    s_con.backup(d_con)
                    backed_up_files.append("conversation_summaries.db")
                except Exception:
                    # Fallback to copy2 if SQLite backup fails: copy .db and WAL/SHM files
                    shutil.copy2(master_db, dest_db)
                    for sidecar in ("-wal", "-shm"):
                        sc_src = master_db.parent / (master_db.name + sidecar)
                        if sc_src.is_file():
                            shutil.copy2(sc_src, snapshot_dir / sc_src.name)
                            backed_up_files.append(sc_src.name)
                    backed_up_files.append("conversation_summaries.db")
                finally:
                    if d_con:
                        try:
                            d_con.close()
                        except Exception:
                            pass
                    if s_con:
                        try:
                            s_con.close()
                        except Exception:
                            pass

            # 2. Backup agyhub_summaries_proto.pb
            master_proto = effective_master / "agyhub_summaries_proto.pb"
            if master_proto.is_file():
                dest_proto = snapshot_dir / "agyhub_summaries_proto.pb"
                shutil.copy2(master_proto, dest_proto)
                backed_up_files.append("agyhub_summaries_proto.pb")

            # 3. Backup annotations directory (.pbtxt files)
            master_anno = effective_master / "annotations"
            if master_anno.is_dir():
                dest_anno = snapshot_dir / "annotations"
                dest_anno.mkdir(parents=True, exist_ok=True)
                for pbtxt in glob.glob(os.path.join(str(master_anno), "*.pbtxt")):
                    shutil.copy2(pbtxt, os.path.join(str(dest_anno), os.path.basename(pbtxt)))
                backed_up_files.append("annotations")

            # 4. Backup state.vscdb entries for antigravityUnifiedStateSync
            vscdb_data: Dict[str, Dict[str, Optional[str]]] = {}
            if candidate_vscdbs:
                for vsc_path in candidate_vscdbs:
                    if not vsc_path.is_file():
                        continue
                    v_con = None
                    try:
                        v_con = sqlite3.connect(str(vsc_path), timeout=15.0)
                        v_cur = v_con.cursor()
                        rows = v_cur.execute(
                            "SELECT key, value FROM ItemTable WHERE key IN ('antigravityUnifiedStateSync.trajectorySummaries', 'antigravityUnifiedStateSync');"
                        ).fetchall()
                        if rows:
                            vscdb_data[str(vsc_path)] = {r[0]: r[1] for r in rows}
                    except Exception:
                        pass
                    finally:
                        if v_con:
                            try:
                                v_con.close()
                            except Exception:
                                pass

            if vscdb_data:
                vsc_file = snapshot_dir / "vscdb_keys.json"
                with open(vsc_file, "w", encoding="utf-8") as vf:
                    json.dump(vscdb_data, vf, indent=2)
                backed_up_files.append("vscdb_keys.json")

            manifest = BackupEntry(
                backup_id=backup_id,
                timestamp=now.isoformat(),
                backup_dir=str(snapshot_dir),
                description=description,
                master_app_dir=str(effective_master),
                files=backed_up_files,
                vscdb_entries_count=len(vscdb_data),
            )

            manifest_file = snapshot_dir / "manifest.json"
            with open(manifest_file, "w", encoding="utf-8") as mf:
                json.dump(asdict(manifest), mf, indent=2)

            # Prune older backups if exceeding limit
            cls.prune_backups(backup_root, max_keep=max_backups)

            return manifest
        except Exception:
            return None

    @classmethod
    def list_backups(cls, user_home: Optional[Union[str, Path]] = None) -> List[BackupEntry]:
        """Lists all existing backup entries, sorted from newest to oldest."""
        backup_root = cls.get_backup_root(user_home)
        backups: List[BackupEntry] = []

        for d in sorted(glob.glob(os.path.join(str(backup_root), "*")), reverse=True):
            if not os.path.isdir(d):
                continue
            manifest_file = os.path.join(d, "manifest.json")
            if os.path.isfile(manifest_file):
                try:
                    with open(manifest_file, "r", encoding="utf-8") as mf:
                        data = json.load(mf)
                    backups.append(BackupEntry(**data))
                except Exception:
                    pass
        return backups

    @classmethod
    def restore_backup(
        cls,
        backup_id_or_path: str,
        user_home: Optional[Union[str, Path]] = None,
    ) -> bool:
        """
        Restores a backup snapshot given its backup ID or directory path.
        Restores conversation_summaries.db, agyhub_summaries_proto.pb,
        annotations, and state.vscdb entries.
        """
        backup_root = cls.get_backup_root(user_home)

        # Resolve snapshot directory
        candidate_dir = Path(backup_id_or_path)
        if not candidate_dir.is_dir():
            candidate_dir = backup_root / backup_id_or_path

        if not candidate_dir.is_dir():
            return False

        manifest_file = candidate_dir / "manifest.json"
        if not manifest_file.is_file():
            return False

        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                data = json.load(mf)
            manifest = BackupEntry(**data)
            target_master = Path(manifest.master_app_dir)
            target_master.mkdir(parents=True, exist_ok=True)

            # 1. Restore conversation_summaries.db
            src_db = candidate_dir / "conversation_summaries.db"
            if src_db.is_file():
                dest_db = target_master / "conversation_summaries.db"
                s_con = None
                d_con = None
                try:
                    s_con = sqlite3.connect(str(src_db), timeout=15.0)
                    d_con = sqlite3.connect(str(dest_db), timeout=15.0)
                    s_con.backup(d_con)
                    d_con.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                    d_con.commit()
                except Exception:
                    shutil.copy2(src_db, dest_db)
                    for sidecar in ("-wal", "-shm"):
                        sc_src = candidate_dir / (src_db.name + sidecar)
                        if sc_src.is_file():
                            shutil.copy2(sc_src, target_master / sc_src.name)
                finally:
                    if d_con:
                        try:
                            d_con.close()
                        except Exception:
                            pass
                    if s_con:
                        try:
                            s_con.close()
                        except Exception:
                            pass

                # Maintain sub-conversations symlink if present
                sub_link = target_master / "conversations" / "conversation_summaries.db"
                if sub_link.is_symlink() or not sub_link.exists():
                    try:
                        if sub_link.exists() or sub_link.is_symlink():
                            sub_link.unlink()
                        sub_link.symlink_to("../conversation_summaries.db")
                    except Exception:
                        pass

            # 2. Restore agyhub_summaries_proto.pb
            src_proto = candidate_dir / "agyhub_summaries_proto.pb"
            if src_proto.is_file():
                dest_proto = target_master / "agyhub_summaries_proto.pb"
                shutil.copy2(src_proto, dest_proto)

            # 3. Restore annotations
            src_anno = candidate_dir / "annotations"
            if src_anno.is_dir():
                dest_anno = target_master / "annotations"
                dest_anno.mkdir(parents=True, exist_ok=True)
                for pbtxt in glob.glob(os.path.join(str(src_anno), "*.pbtxt")):
                    shutil.copy2(pbtxt, os.path.join(str(dest_anno), os.path.basename(pbtxt)))

            # 4. Restore state.vscdb keys
            vsc_file = candidate_dir / "vscdb_keys.json"
            if vsc_file.is_file():
                with open(vsc_file, "r", encoding="utf-8") as vf:
                    vsc_records: Dict[str, Dict[str, Optional[str]]] = json.load(vf)
                for vsc_path_str, keys_dict in vsc_records.items():
                    if not os.path.isfile(vsc_path_str):
                        continue
                    v_con = None
                    try:
                        v_con = sqlite3.connect(vsc_path_str, timeout=15.0)
                        v_cur = v_con.cursor()
                        for k, v in keys_dict.items():
                            if v is not None:
                                v_cur.execute(
                                    "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?);",
                                    (k, v),
                                )
                        v_con.commit()
                    except Exception:
                        pass
                    finally:
                        if v_con:
                            try:
                                v_con.close()
                            except Exception:
                                pass

            return True
        except Exception:
            return False

    @classmethod
    def prune_backups(cls, backup_root: Path, max_keep: int = 10) -> None:
        """Prunes oldest backup folders keeping only max_keep most recent snapshots."""
        try:
            dirs = sorted(
                [Path(p) for p in glob.glob(os.path.join(str(backup_root), "*")) if os.path.isdir(p)],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if len(dirs) > max_keep:
                for old_dir in dirs[max_keep:]:
                    shutil.rmtree(old_dir, ignore_errors=True)
        except Exception:
            pass
