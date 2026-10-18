"""
Comprehensive purge of conversations across all persistence layers.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from antigravity_suite.config import get_user_home
from antigravity_suite.history.deletion_rpc import notify_language_servers_deletion
from antigravity_suite.history.deletion_storage import purge_conversation_from_app_storage
from antigravity_suite.history.deletion_trash import archive_deleted_conversation
from antigravity_suite.history.deletion_vscdb import purge_conversation_from_vscdb


def purge_conversation(
    conv_id: str,
    effective_master: Path,
    con: sqlite3.Connection,
    candidate_vscdbs: List[Path],
    conv_pools: List[str],
    brain_pools: List[str],
    all_summaries: Dict[str, bytes],
    user_home: Optional[Path] = None,
) -> None:
    """Completely purges conversation across all persistence layers."""
    archive_deleted_conversation(conv_id, effective_master, user_home, con=con)
    notify_language_servers_deletion(conv_id, effective_master=effective_master)

    for vscdb in candidate_vscdbs:
        purge_conversation_from_vscdb(vscdb, conv_id)

    purge_conversation_from_app_storage(conv_id, user_home=user_home)

    cur = con.cursor()
    cur.execute("DELETE FROM conversation_summaries WHERE conversation_id = ?;", (conv_id,))
    try:
        cur.execute("DELETE FROM conversations_fts WHERE conversation_id = ?;", (conv_id,))
    except Exception:
        pass
    con.commit()

    home_dir = user_home or get_user_home()
    for prof_db in home_dir.glob(".antigravity-profile*/conversation_summaries.db"):
        if prof_db.is_file() and prof_db.resolve() != (effective_master / "conversation_summaries.db").resolve():
            try:
                with sqlite3.connect(str(prof_db), timeout=5.0) as p_con:
                    p_con.execute("DELETE FROM conversation_summaries WHERE conversation_id = ?;", (conv_id,))
                    try:
                        p_con.execute("DELETE FROM conversations_fts WHERE conversation_id = ?;", (conv_id,))
                    except Exception:
                        pass
                    p_con.commit()
            except Exception:
                pass

    all_summaries.pop(conv_id, None)

    for c_pool in [effective_master / "conversations"] + [Path(p) for p in conv_pools]:
        for ext in [".db", ".db-wal", ".db-shm", ".pb", ".json"]:
            target_f = c_pool / f"{conv_id}{ext}"
            if target_f.exists():
                try:
                    target_f.unlink()
                except Exception:
                    pass

    anno_f = effective_master / "annotations" / f"{conv_id}.pbtxt"
    if anno_f.exists():
        try:
            anno_f.unlink()
        except Exception:
            pass

    for b_pool in [effective_master / "brain"] + [Path(p) for p in brain_pools]:
        target_b = b_pool / conv_id
        if target_b.is_dir():
            try:
                trash_dir = b_pool / ".trash"
                trash_dir.mkdir(parents=True, exist_ok=True)
                dest = trash_dir / conv_id
                if dest.exists():
                    shutil.rmtree(dest, ignore_errors=True)
                shutil.move(str(target_b), str(dest))
            except Exception:
                try:
                    shutil.rmtree(target_b, ignore_errors=True)
                except Exception:
                    pass
