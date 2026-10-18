"""
Discovers recently opened workspace roots from VS Code state.vscdb storage.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote, urlsplit

from antigravity_suite.config import get_user_home


def discover_roots_from_vscdb(user_home: Optional[Path] = None) -> List[str]:
    """Extracts authentic workspace roots from IDE globalStorage state.vscdb."""
    home = user_home or get_user_home()
    roots: List[str] = []
    patterns = [
        os.path.join(str(home), ".config", "Antigravity*", "User", "globalStorage", "state.vscdb"),
        os.path.join(str(home), ".config", "antigravity*", "User", "globalStorage", "state.vscdb"),
        os.path.join(str(home), ".antigravity*", "User", "globalStorage", "state.vscdb"),
    ]
    seen = set()
    for pat in patterns:
        for db_p in glob.glob(pat):
            if not os.path.isfile(db_p) or db_p in seen:
                continue
            seen.add(db_p)
            try:
                with sqlite3.connect(db_p, timeout=1.0) as con:
                    cur = con.cursor()
                    cur.execute("SELECT value FROM ItemTable WHERE key = 'history.recentlyOpenedPathsList'")
                    row = cur.fetchone()
                    if row and row[0]:
                        data = json.loads(row[0])
                        for entry in data.get("entries", []):
                            furi = entry.get("folderUri") or entry.get("workspace", {}).get("configPath")
                            if furi and str(furi).startswith("file://"):
                                p_str = unquote(urlsplit(str(furi)).path).rstrip("/")
                                if p_str not in ("/tmp", "/var/tmp", str(home), "") and p_str.count("/") > 2:
                                    roots.append(str(furi).rstrip("/"))
            except Exception:
                pass
    return roots
