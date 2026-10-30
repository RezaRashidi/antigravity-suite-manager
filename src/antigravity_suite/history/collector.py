"""History Store File Collector and Master Directory Manager."""
from __future__ import annotations
import glob, os, re, shutil, sqlite3
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple, Union

def setup_master_directories(effective_master: Path) -> Tuple[Path, Path, Path, Path, Path]:
    """Creates canonical directories and resolves master database symlinks."""
    master_conv_dir, master_brain_dir = effective_master / "conversations", effective_master / "brain"
    master_sum_db, master_proto, master_anno = effective_master / "conversation_summaries.db", effective_master / "agyhub_summaries_proto.pb", effective_master / "annotations"
    sub_sum_db = master_conv_dir / "conversation_summaries.db"
    master_conv_dir.mkdir(parents=True, exist_ok=True)
    master_brain_dir.mkdir(parents=True, exist_ok=True)
    master_anno.mkdir(parents=True, exist_ok=True)
    if sub_sum_db.exists() or sub_sum_db.is_symlink():
        if not master_sum_db.exists() and not sub_sum_db.is_symlink():
            shutil.move(str(sub_sum_db), str(master_sum_db))
        elif sub_sum_db.is_symlink() or sub_sum_db.is_file():
            os.remove(str(sub_sum_db))
    return master_conv_dir, master_brain_dir, master_sum_db, master_proto, master_anno


def collect_all_conversation_ids(
    master_conv_dir: Path,
    existing_rows: Dict[str, Tuple],
    extra_ids: Optional[Iterable[str]] = None,
    tombstones: Optional[Set[str]] = None,
    master_brain_dir: Optional[Path] = None,
    subagents: Optional[Set[str]] = None,
) -> Set[str]:
    """Scans databases, protobufs, and existing rows for 36-char UUIDs, skipping tombstones and subagents."""
    all_conv_ids: Set[str] = set()
    uuid_pattern = re.compile(r"^[0-9a-fA-F-]{36}$")
    excluded = (tombstones or set()) | (subagents or set())

    for db_f in glob.glob(os.path.join(str(master_conv_dir), "*.db")):
        cid = os.path.basename(db_f)[:-3]
        if uuid_pattern.match(cid) and cid not in excluded:
            all_conv_ids.add(cid)

    for pb_f in glob.glob(os.path.join(str(master_conv_dir), "*.pb")):
        cid = os.path.basename(pb_f)[:-3]
        if uuid_pattern.match(cid) and cid not in excluded:
            all_conv_ids.add(cid)

    for cid in existing_rows.keys():
        if uuid_pattern.match(cid) and cid not in excluded:
            all_conv_ids.add(cid)

    if extra_ids:
        for cid in extra_ids:
            if uuid_pattern.match(cid) and cid not in excluded:
                all_conv_ids.add(cid)

    return all_conv_ids


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
            from antigravity_suite.proto.trajectory import parse_trajectory_metadata_blob
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
