"""
Subagent Detection, Isolation, and History Purge Helpers.

Prevents child subagents from leaking into conversation history, SQLite summaries,
and VS Code/Antigravity IDE chat sidebar states.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Iterable, Optional, Set, Union

UUID_REGEX = re.compile(r"^[0-9a-fA-F-]{36}$")


def discover_subagent_uuids(brain_pools: Iterable[Union[str, Path]]) -> Set[str]:
    """Scans all brain pools for child subagent metadata JSON files."""
    subagent_ids: Set[str] = set()
    for pool in brain_pools:
        p_str = str(pool)
        if not os.path.isdir(p_str):
            continue
        pattern = os.path.join(p_str, "*", ".system_generated", "subagents", "*.json")
        for f_path in glob.glob(pattern):
            cid = os.path.basename(f_path)[:-5]
            if UUID_REGEX.match(cid):
                subagent_ids.add(cid)
            try:
                with open(f_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    c = data.get("conversationId")
                    if c and UUID_REGEX.match(c):
                        subagent_ids.add(c)
            except Exception:
                pass
    return subagent_ids


def purge_subagents_from_store(
    master_conv_dir: Path,
    con: sqlite3.Connection,
    subagent_ids: Optional[Set[str]] = None,
) -> int:
    """Removes mistakenly synthesized databases and summary records for subagents."""
    purged = 0
    cur = con.cursor()
    ids_to_purge = set(subagent_ids or ())

    rows = cur.execute(
        "SELECT conversation_id FROM conversation_summaries WHERE parent_conversation_id != '' OR nesting_depth > 0;"
    ).fetchall()
    for r in rows:
        if r[0]:
            ids_to_purge.add(r[0])

    for sid in ids_to_purge:
        db_f = master_conv_dir / f"{sid}.db"
        if db_f.is_file():
            try:
                db_f.unlink()
                purged += 1
            except Exception:
                pass

    if ids_to_purge:
        cur.executemany(
            "DELETE FROM conversation_summaries WHERE conversation_id = ?;",
            [(s,) for s in ids_to_purge],
        )
        try:
            cur.executemany(
                "DELETE FROM conversations_fts WHERE conversation_id = ?;",
                [(s,) for s in ids_to_purge],
            )
        except Exception:
            pass

    cur.execute(
        "DELETE FROM conversation_summaries WHERE parent_conversation_id != '' OR nesting_depth > 0;"
    )
    con.commit()
    return purged
