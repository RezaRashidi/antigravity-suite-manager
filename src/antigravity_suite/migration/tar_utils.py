"""
Archive handling, tar packaging, and step counting utilities.
"""

from __future__ import annotations

import datetime
import os
import tarfile
from typing import Optional, Set


def get_timestamp() -> str:
    """Returns current timestamp string in YYYYmmdd_HHMMSS format."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def format_size(bytes_val: float) -> str:
    """Formats bytes value into human-readable size string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"


def safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    """Safely extracts tar files preventing path traversal and handling Python 3.12+ filter."""
    try:
        tar.extractall(path=path, filter="data")
    except TypeError:
        tar.extractall(path=path)


def get_db_step_count(db_path: str) -> int:
    """Safely queries SQLite database step count for precedence comparison."""
    if not os.path.isfile(db_path):
        return -1
    try:
        import sqlite3
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as con:
            row = con.execute("SELECT count(*) FROM steps").fetchone()
            return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return -1


def add_path_safe(tar: tarfile.TarFile, src_path: str, arc_prefix: str, visited: Optional[Set[str]] = None) -> None:
    """Recursively adds file or directory to tar archive resolving symlinks safely."""
    if visited is None:
        visited = set()
    if os.path.islink(src_path):
        if not os.path.exists(src_path): return
        real_p = os.path.realpath(src_path)
        if real_p in visited: return
        visited.add(real_p)
        if os.path.isdir(real_p):
            add_path_safe(tar, real_p, arc_prefix, visited); return
        src_path = real_p

    if os.path.isfile(src_path):
        try:
            ti = tar.gettarinfo(src_path, arcname=arc_prefix)
            with open(src_path, 'rb') as f: tar.addfile(ti, f)
        except Exception: pass
        return

    if os.path.isdir(src_path):
        real_d = os.path.realpath(src_path)
        if real_d in visited: return
        visited.add(real_d)
        try:
            ti = tar.gettarinfo(src_path, arcname=arc_prefix)
            tar.addfile(ti)
        except Exception: pass
        try: entries = sorted(os.listdir(src_path))
        except Exception: return
        for item in entries:
            add_path_safe(tar, os.path.join(src_path, item), os.path.join(arc_prefix, item), visited)
