"""
Test Data Manager for Antigravity Suite Manager.

Automatically manages and synchronizes local test fixtures and database snapshots
into a gitignored repository directory (`tests/test_data/`).
Ensures tests can run against real host data when available, or clean fallback fixtures
in CI/CD environments, without ever tracking personal data in Git.
"""

import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional


def get_repo_root() -> Path:
    """Returns the absolute path to the repository root."""
    return Path(__file__).resolve().parent.parent


def get_test_data_dir() -> Path:
    """Returns the path to the gitignored tests/test_data directory."""
    test_data_dir = get_repo_root() / "tests" / "test_data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    return test_data_dir


def copy_sqlite_safely(src: Path, dst: Path) -> bool:
    """Safely copies a SQLite database, handling WAL/SHM mode."""
    if not src.exists() or not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Use SQLite backup API to safely snapshot even if source is currently in use
        con_src = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        con_dst = sqlite3.connect(str(dst))
        with con_dst:
            con_src.backup(con_dst)
        con_src.close()
        con_dst.close()
        return True
    except Exception:
        # Fallback to file copy
        try:
            shutil.copy2(str(src), str(dst))
            wal = src.with_name(src.name + "-wal")
            shm = src.with_name(src.name + "-shm")
            if wal.exists():
                shutil.copy2(str(wal), str(dst.with_name(dst.name + "-wal")))
            if shm.exists():
                shutil.copy2(str(shm), str(dst.with_name(dst.name + "-shm")))
            return True
        except Exception:
            return False


def discover_host_gemini_dirs() -> List[Path]:
    """Finds existing host Gemini directories."""
    home = Path.home()
    candidates = [
        home / ".gemini" / "antigravity",
        home / ".gemini",
        home / ".gemide" / "antigravity",
        home / ".gemide",
        home / ".gemini-ide",
    ]
    env_dir = os.environ.get("ANTIGRAVITY_GEMINI_DIR")
    if env_dir:
        candidates.insert(0, Path(env_dir))
    return [c for c in candidates if c.is_dir()]


def discover_host_ide_vscdb() -> Optional[Path]:
    """Finds existing host state.vscdb for Antigravity IDE."""
    home = Path.home()
    candidates = [
        home / ".config" / "Antigravity IDE" / "User" / "globalStorage" / "state.vscdb",
        home / ".config" / "Antigravity" / "User" / "globalStorage" / "state.vscdb",
        home / ".config" / "Code" / "User" / "globalStorage" / "state.vscdb",
        home / "Library" / "Application Support" / "Antigravity IDE" / "User" / "globalStorage" / "state.vscdb",
        home / "AppData" / "Roaming" / "Antigravity IDE" / "User" / "globalStorage" / "state.vscdb",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def sync_test_data(
    dest_dir: Optional[Path] = None,
    max_sample_conversations: int = 5,
    force: bool = False,
) -> Path:
    """
    Synchronizes host data into the gitignored test_data directory.
    If host data is not available (e.g. CI/CD), creates self-contained mock fixtures.
    """
    target = dest_dir or get_test_data_dir()
    gemini_target = target / "gemini"
    ide_target = target / "ide"
    workspaces_target = target / "workspaces"

    gemini_target.mkdir(parents=True, exist_ok=True)
    ide_target.mkdir(parents=True, exist_ok=True)
    workspaces_target.mkdir(parents=True, exist_ok=True)

    copied_db = False
    copied_vscdb = False

    # 1. Sync conversation_summaries.db from host
    target_conv_db = gemini_target / "conversation_summaries.db"
    if force or not target_conv_db.exists() or target_conv_db.stat().st_size == 0:
        for host_dir in discover_host_gemini_dirs():
            cand_db = host_dir / "conversation_summaries.db"
            if cand_db.is_file():
                if copy_sqlite_safely(cand_db, target_conv_db):
                    copied_db = True
                    break

    # Fallback mock conversation_summaries.db if no host DB found
    if not target_conv_db.exists() or target_conv_db.stat().st_size == 0:
        con = sqlite3.connect(str(target_conv_db))
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                conversation_id TEXT PRIMARY KEY,
                title TEXT,
                step_count INTEGER,
                updated_at INTEGER,
                workspace_uri TEXT
            );
            """
        )
        con.execute(
            """
            INSERT OR REPLACE INTO conversation_summaries VALUES
            ('mock-conv-001', 'Sample Workflow Fix', 5, 1713000000, 'file:///tmp/sample-project'),
            ('mock-conv-002', 'Deploy Pipeline Config', 8, 1713010000, 'file:///tmp/cloud-app');
            """
        )
        con.commit()
        con.close()

    # 2. Sync state.vscdb from host
    target_vscdb = ide_target / "state.vscdb"
    if force or not target_vscdb.exists() or target_vscdb.stat().st_size == 0:
        host_vscdb = discover_host_ide_vscdb()
        if host_vscdb and copy_sqlite_safely(host_vscdb, target_vscdb):
            copied_vscdb = True

    # Fallback mock state.vscdb if no host vscdb found
    if not target_vscdb.exists() or target_vscdb.stat().st_size == 0:
        con = sqlite3.connect(str(target_vscdb))
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS ItemTable (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        sample_workspaces = json.dumps(["file:///tmp/sample-project", "file:///tmp/cloud-app"])
        con.execute(
            "INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync.sidebarWorkspaces', ?);",
            (sample_workspaces,),
        )
        con.commit()
        con.close()

    # 3. Sync project configurations from host
    projects_target = gemini_target / "config" / "projects"
    projects_target.mkdir(parents=True, exist_ok=True)
    found_projects = False
    for host_dir in discover_host_gemini_dirs():
        host_projects_dir = host_dir / "config" / "projects"
        if host_projects_dir.is_dir():
            for pjson in host_projects_dir.glob("*.json"):
                try:
                    shutil.copy2(str(pjson), str(projects_target / pjson.name))
                    found_projects = True
                except Exception:
                    pass
            if found_projects:
                break

    # Fallback mock projects if none found
    if not found_projects and not any(projects_target.glob("*.json")):
        sample_project = {
            "id": "mock-pid-0001",
            "name": "sample-project",
            "projectResources": {
                "resources": [{"folderUri": "file:///tmp/sample-project"}]
            },
        }
        with open(projects_target / "mock-pid-0001.json", "w", encoding="utf-8") as f:
            json.dump(sample_project, f, indent=2)

    # 4. Sync sample protobuf files if present
    for host_dir in discover_host_gemini_dirs():
        for pb_name in ["agyhub_summaries_proto.pb", "agyhub_summaries.pb", "jetbox_summaries.pb"]:
            pb_src = host_dir / pb_name
            if pb_src.is_file():
                try:
                    shutil.copy2(str(pb_src), str(gemini_target / pb_name))
                except Exception:
                    pass

    # 5. Sync sample conversations/transcripts (up to max_sample_conversations)
    conv_target = gemini_target / "conversations"
    conv_target.mkdir(parents=True, exist_ok=True)
    count = 0
    for host_dir in discover_host_gemini_dirs():
        for cand_name in ["brain", "conversations", "c"]:
            cand_path = host_dir / cand_name
            if cand_path.is_dir():
                for sub in sorted(cand_path.iterdir()):
                    if count >= max_sample_conversations:
                        break
                    if sub.is_dir():
                        dest_sub = conv_target / sub.name
                        if not dest_sub.exists():
                            try:
                                # Copy only transcript files or light logs, skip huge caches
                                dest_sub.mkdir(parents=True, exist_ok=True)
                                for item in sub.rglob("*transcript*"):
                                    if item.is_file() and item.stat().st_size < 5 * 1024 * 1024:
                                        rel = item.relative_to(sub)
                                        target_file = dest_sub / rel
                                        target_file.parent.mkdir(parents=True, exist_ok=True)
                                        shutil.copy2(str(item), str(target_file))
                                count += 1
                            except Exception:
                                pass
                if count > 0:
                    break

    return target


def get_isolated_workspace(name: str = "run") -> Path:
    """
    Returns an isolated, clean workspace directory inside tests/test_data/workspaces/.
    This ensures test runs stay inside the gitignored repo workspace instead of /tmp.
    """
    ws = get_test_data_dir() / "workspaces" / name
    if ws.exists():
        shutil.rmtree(str(ws), ignore_errors=True)
    ws.mkdir(parents=True, exist_ok=True)
    return ws
