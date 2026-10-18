"""
Trash archive and recovery operations for deleted conversations.
"""

from __future__ import annotations

import base64
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Optional

from antigravity_suite.config import get_user_home
from antigravity_suite.history.deletion_manifest import load_manifest, save_manifest


def archive_deleted_conversation(conv_id: str, effective_master: Path, user_home: Optional[Path] = None, con: Optional[sqlite3.Connection] = None) -> Path:
    """Creates a non-destructive safety archive of the deleted conversation."""
    home = user_home or get_user_home()
    trash_dir = home / ".config" / "antigravity" / "backups" / "trash" / conv_id
    trash_dir.mkdir(parents=True, exist_ok=True)

    for f_name in [f"{conv_id}.db", f"{conv_id}.pbtxt"]:
        src = (effective_master / "conversations" if f_name.endswith(".db") else effective_master / "annotations") / f_name
        if src.is_file():
            try:
                shutil.copy2(src, trash_dir / f_name)
            except Exception:
                pass

    brain_dir = effective_master / "brain" / conv_id
    if brain_dir.is_dir():
        try:
            dest_brain = trash_dir / "brain"
            if dest_brain.exists():
                shutil.rmtree(dest_brain, ignore_errors=True)
            shutil.copytree(brain_dir, dest_brain)
        except Exception:
            pass

    if con:
        try:
            cur = con.cursor()
            row = cur.execute("SELECT * FROM conversation_summaries WHERE conversation_id = ?;", (conv_id,)).fetchone()
            if row:
                col_names = [d[0] for d in cur.description]
                row_dict = {col_names[i]: (base64.b64encode(v).decode("ascii") if isinstance(v, (bytes, bytearray)) else v) for i, v in enumerate(row)}
                (trash_dir / "summary.json").write_text(json.dumps(row_dict, indent=2), encoding="utf-8")
        except Exception:
            pass
    return trash_dir


def restore_chat_from_trash(conv_id: str, effective_master: Path, user_home: Optional[Path] = None) -> bool:
    """Restores a deleted conversation from the trash archive and untombstones it."""
    home = user_home or get_user_home()
    trash_dir = home / ".config" / "antigravity" / "backups" / "trash" / conv_id
    if not trash_dir.is_dir():
        return False

    t_db = trash_dir / f"{conv_id}.db"
    if t_db.is_file():
        dest_db = effective_master / "conversations" / f"{conv_id}.db"
        dest_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(t_db, dest_db)

    t_anno = trash_dir / f"{conv_id}.pbtxt"
    if t_anno.is_file():
        dest_anno = effective_master / "annotations" / f"{conv_id}.pbtxt"
        dest_anno.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(t_anno, dest_anno)

    t_brain = trash_dir / "brain"
    if t_brain.is_dir():
        dest_brain = effective_master / "brain" / conv_id
        dest_brain.parent.mkdir(parents=True, exist_ok=True)
        if dest_brain.exists():
            shutil.rmtree(dest_brain, ignore_errors=True)
        shutil.copytree(t_brain, dest_brain)

    manifest = load_manifest(effective_master)
    manifest.get("tombstones", {}).pop(conv_id, None)
    for k in ["known_ids", "known_app_ids", "known_ide_ids"]:
        if conv_id not in manifest.get(k, []):
            manifest.setdefault(k, []).append(conv_id)
    save_manifest(effective_master, manifest)
    return True
