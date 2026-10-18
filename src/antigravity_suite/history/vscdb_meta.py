"""
Trajectory Database Metadata Extraction.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Tuple, Union

from antigravity_suite.proto.trajectory import parse_trajectory_metadata_blob


def get_db_trajectory_meta(db_path: Union[str, Path]) -> Tuple[Optional[str], Optional[str]]:
    """Reads workspace_uri and project_id from trajectory_metadata_blob if present."""
    p = Path(db_path)
    if not p.is_file():
        return None, None
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=15.0)
        row = conn.cursor().execute("SELECT data FROM trajectory_metadata_blob WHERE id = 'main';").fetchone()
        if row and row[0]:
            meta = parse_trajectory_metadata_blob(row[0])
            uris = meta.get("workspace_uris", [])
            w_uri = uris[0] if uris else meta.get("workspace_uri")
            return w_uri, meta.get("project_id")
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return None, None
