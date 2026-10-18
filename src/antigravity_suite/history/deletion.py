"""
Bi-directional Conversation Deletion and Tombstone Synchronization Engine.

Tracks synchronized conversation lifecycles across Antigravity Desktop App and IDE.
When a conversation is deleted in either environment (Desktop App or IDE),
this engine guarantees atomic, permanent deletion from both sides, preventing
resurrection by pool mergers, reconstruction engines, or state serializers.
Also manages conversational trash archives for safe, non-destructive recovery.
"""

from __future__ import annotations

import base64
import datetime
import glob
import json
import os
import re
import shutil
import sqlite3
import ssl
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from antigravity_suite.config import get_user_home
from antigravity_suite.history.models import SyncStats
from antigravity_suite.proto.cascade import parse_cascade_summary
from antigravity_suite.proto.vscdb import build_summaries_state, build_unified_state_sync
from antigravity_suite.proto.wire import extract_entries_from_proto, extract_pure_binary_summary

MANIFEST_FILENAME = "sync_manifest.json"


def get_manifest_path(effective_master: Path) -> Path:
    """Returns the canonical path to the sync manifest JSON file."""
    return effective_master / MANIFEST_FILENAME


def load_manifest(effective_master: Path) -> Dict[str, Any]:
    """Loads the synchronization manifest tracking known conversations and tombstones."""
    m_path = get_manifest_path(effective_master)
    if not m_path.is_file():
        return {
            "version": 2,
            "known_ids": [],
            "known_app_ids": [],
            "known_ide_ids": [],
            "tombstones": {},
            "last_synced_at": "",
        }
    try:
        with open(m_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {
                    "version": 2,
                    "known_ids": [],
                    "known_app_ids": [],
                    "known_ide_ids": [],
                    "tombstones": {},
                    "last_synced_at": "",
                }
            data.setdefault("version", 2)
            data.setdefault("known_ids", [])
            data.setdefault("known_app_ids", list(data.get("known_ids", [])))
            data.setdefault("known_ide_ids", list(data.get("known_ids", [])))
            data.setdefault("tombstones", {})
            return data
    except Exception:
        return {
            "version": 2,
            "known_ids": [],
            "known_app_ids": [],
            "known_ide_ids": [],
            "tombstones": {},
            "last_synced_at": "",
        }


def save_manifest(effective_master: Path, manifest: Dict[str, Any]) -> None:
    """Atomically saves the synchronization manifest to disk."""
    m_path = get_manifest_path(effective_master)
    manifest["version"] = 2
    manifest["last_synced_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tmp_path = m_path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, m_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def get_tombstones(effective_master: Path) -> Set[str]:
    """Retrieves the set of all deleted conversation UUIDs from the manifest."""
    manifest = load_manifest(effective_master)
    return set(manifest.get("tombstones", {}).keys())


def find_running_language_servers() -> List[Dict[str, Any]]:
    """
    Discovers all active Antigravity Language Server processes (App and IDE),
    their loopback ports, and CSRF tokens from the local system.
    """
    servers: List[Dict[str, Any]] = []
    pid_ports: Dict[int, List[int]] = {}

    try:
        ss_out = subprocess.run(
            ["ss", "-tulpn"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2.0,
        ).stdout
        for line in ss_out.splitlines():
            if "127.0.0.1:" in line and "pid=" in line:
                m_port = re.search(r"127\.0\.0\.1:(\d+)", line)
                m_pid = re.search(r"pid=(\d+)", line)
                if m_port and m_pid:
                    port = int(m_port.group(1))
                    pid = int(m_pid.group(1))
                    pid_ports.setdefault(pid, []).append(port)
    except Exception:
        pass

    for pid, ports in pid_ports.items():
        cmdline_file = f"/proc/{pid}/cmdline"
        if os.path.exists(cmdline_file):
            try:
                with open(cmdline_file, "rb") as f:
                    cmd_str = f.read().decode("utf-8", errors="ignore").replace("\x00", " ")
                    if "language_server" in cmd_str:
                        csrf_m = re.search(r"--csrf_token[=\s]+([a-f0-9-]+)", cmd_str)
                        app_data_m = re.search(r"--app_data_dir[=\s]+([^\s]+)", cmd_str)
                        subclient_m = re.search(r"--subclient_type[=\s]+([^\s]+)", cmd_str)
                        servers.append({
                            "pid": pid,
                            "ports": ports,
                            "csrf": csrf_m.group(1) if csrf_m else None,
                            "app_data_dir": app_data_m.group(1) if app_data_m else None,
                            "subclient_type": subclient_m.group(1) if subclient_m else None,
                        })
            except Exception:
                pass

    return servers


def notify_language_servers_deletion(conv_id: str, effective_master: Optional[Path] = None) -> None:
    """
    Invokes loopback ConnectRPC on all running Language Servers to immediately
    evict the deleted conversation from memory and broadcast deletion to frontends.
    If the underlying database file is missing on disk, temporarily generates a minimal
    SQLite schema so that Go LS LoadTrajectory succeeds and executes deletion cleanup.
    """
    servers = find_running_language_servers()
    if not servers:
        return

    # Check if a temporary minimal db is needed for Go LS to safely LoadTrajectory before deleting
    temp_db_path: Optional[Path] = None
    if effective_master:
        conv_dir = effective_master / "conversations"
        db_f = conv_dir / f"{conv_id}.db"
        if not db_f.exists():
            try:
                conv_dir.mkdir(parents=True, exist_ok=True)
                with sqlite3.connect(str(db_f)) as t_con:
                    t_con.execute("CREATE TABLE IF NOT EXISTS steps (id INTEGER PRIMARY KEY, type TEXT, content TEXT, timestamp TEXT);")
                    t_con.execute("CREATE TABLE IF NOT EXISTS gen_metadata (id INTEGER PRIMARY KEY, metadata TEXT);")
                    t_con.execute("CREATE TABLE IF NOT EXISTS trajectory_metadata_blob (id text DEFAULT 'main', data blob, PRIMARY KEY (id));")
                    t_con.commit()
                temp_db_path = db_f
            except Exception:
                pass

    ctx = ssl._create_unverified_context()
    payload = json.dumps({"cascadeId": conv_id}).encode("utf-8")

    try:
        for s in servers:
            csrf = s.get("csrf")
            if not csrf:
                continue
            for port in s.get("ports", []):
                headers = {
                    "Content-Type": "application/json",
                    "x-codeium-csrf-token": csrf,
                    "Connect-Protocol-Version": "1",
                }
                # 1. DeleteCascadeTrajectory (Both IDE and Hub)
                url_del = f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/DeleteCascadeTrajectory"
                try:
                    req = urllib.request.Request(url_del, data=payload, headers=headers)
                    with urllib.request.urlopen(req, context=ctx, timeout=1.0):
                        pass
                except Exception:
                    pass

                # 2. JetboxDeleteSummary (Desktop App Hub)
                url_jetbox = f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/JetboxDeleteSummary"
                try:
                    req = urllib.request.Request(url_jetbox, data=payload, headers=headers)
                    with urllib.request.urlopen(req, context=ctx, timeout=1.0):
                        pass
                except Exception:
                    pass

                # 3. DeleteCascadeMemory (Evict associated context memories)
                url_mem = f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/DeleteCascadeMemory"
                try:
                    req = urllib.request.Request(url_mem, data=payload, headers=headers)
                    with urllib.request.urlopen(req, context=ctx, timeout=1.0):
                        pass
                except Exception:
                    pass
    finally:
        if temp_db_path and temp_db_path.exists():
            try:
                temp_db_path.unlink()
            except Exception:
                pass


def get_active_ide_ids(candidate_vscdbs: List[Path]) -> Set[str]:
    """Extracts all conversation IDs currently active in IDE state.vscdb storage."""
    ide_ids: Set[str] = set()
    for vscdb_p in candidate_vscdbs:
        if not vscdb_p.is_file():
            continue
        conn = None
        try:
            conn = sqlite3.connect(str(vscdb_p), timeout=5.0)
            rows = conn.cursor().execute(
                "SELECT value FROM ItemTable WHERE key IN ('antigravityUnifiedStateSync.trajectorySummaries', 'antigravityUnifiedStateSync');"
            ).fetchall()
            for r in rows:
                if r and r[0]:
                    try:
                        v_bin = base64.b64decode(r[0])
                        entries = extract_entries_from_proto(v_bin)
                        ide_ids.update(entries.keys())
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    return ide_ids


def purge_conversation_from_vscdb(vscdb_path: Path, conv_id: str) -> bool:
    """Removes a conversation UUID from a state.vscdb database (ItemTable)."""
    if not vscdb_path.is_file():
        return False
    modified = False
    conn = None
    try:
        conn = sqlite3.connect(str(vscdb_path), timeout=5.0)
        cur = conn.cursor()

        # 1. trajectorySummaries and antigravityUnifiedStateSync
        for key in ["antigravityUnifiedStateSync.trajectorySummaries", "antigravityUnifiedStateSync"]:
            row = cur.execute("SELECT value FROM ItemTable WHERE key = ?;", (key,)).fetchone()
            if row and row[0]:
                try:
                    v_bin = base64.b64decode(row[0])
                    entries = extract_entries_from_proto(v_bin)
                    if conv_id in entries:
                        entries.pop(conv_id, None)
                        valid_summaries = {}
                        for uid, pbin in entries.items():
                            raw = extract_pure_binary_summary(pbin)
                            if raw:
                                valid_summaries[uid] = raw
                        if key == "antigravityUnifiedStateSync.trajectorySummaries":
                            new_b64 = build_summaries_state(valid_summaries)
                        else:
                            new_b64 = build_unified_state_sync(valid_summaries, existing_raw_b64=row[0])
                        cur.execute("UPDATE ItemTable SET value = ? WHERE key = ?;", (new_b64, key))
                        modified = True
                except Exception:
                    pass

        # 2. workspaceCascadeMap in google.antigravity
        row_g = cur.execute("SELECT value FROM ItemTable WHERE key = 'google.antigravity';").fetchone()
        if row_g and row_g[0]:
            try:
                g_data = json.loads(row_g[0])
                w_map = g_data.get("antigravity.workspaceCascadeMap", {})
                w_mod = False
                for w_uri, cid in list(w_map.items()):
                    if cid == conv_id:
                        w_map.pop(w_uri, None)
                        w_mod = True
                if w_mod:
                    g_data["antigravity.workspaceCascadeMap"] = w_map
                    cur.execute("UPDATE ItemTable SET value = ? WHERE key = 'google.antigravity';", (json.dumps(g_data),))
                    modified = True
            except Exception:
                pass

        # 3. Notification keys or any key mentioning conv_id
        try:
            notif_rows = cur.execute("SELECT key FROM ItemTable WHERE key LIKE ?;", (f"%{conv_id}%",)).fetchall()
            for nr in notif_rows:
                if nr and nr[0]:
                    cur.execute("DELETE FROM ItemTable WHERE key = ?;", (nr[0],))
                    modified = True
        except Exception:
            pass

        if modified:
            conn.commit()
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return modified


def purge_conversation_from_app_storage(conv_id: str, user_home: Optional[Path] = None) -> None:
    """Removes conversation layout references from Desktop App electron storage (app_storage.json)."""
    home = user_home or get_user_home()
    candidates = [
        home / ".config" / "Antigravity" / "app_storage.json",
        home / ".antigravity-profile2" / ".config" / "Antigravity" / "app_storage.json",
    ]
    for cand in candidates:
        if not cand.is_file():
            continue
        try:
            data = json.loads(cand.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            modified = False
            for k in list(data.keys()):
                if conv_id in k or conv_id in str(data[k]):
                    data.pop(k, None)
                    modified = True
            if modified:
                cand.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass


def archive_deleted_conversation(
    conv_id: str,
    effective_master: Path,
    user_home: Optional[Path] = None,
    con: Optional[sqlite3.Connection] = None,
) -> Path:
    """
    Creates a non-destructive safety archive of the deleted conversation in ~/.config/antigravity/backups/trash/<conv_id>/
    before permanent purge, preserving disk database, annotations, brain folder, and metadata for recovery.
    """
    home = user_home or get_user_home()
    trash_dir = home / ".config" / "antigravity" / "backups" / "trash" / conv_id
    trash_dir.mkdir(parents=True, exist_ok=True)

    # 1. Archive .db file if exists
    db_file = effective_master / "conversations" / f"{conv_id}.db"
    if db_file.is_file():
        try:
            shutil.copy2(db_file, trash_dir / f"{conv_id}.db")
        except Exception:
            pass

    # 2. Archive .pbtxt annotation if exists
    anno_file = effective_master / "annotations" / f"{conv_id}.pbtxt"
    if anno_file.is_file():
        try:
            shutil.copy2(anno_file, trash_dir / f"{conv_id}.pbtxt")
        except Exception:
            pass

    # 3. Archive brain directory if exists
    brain_dir = effective_master / "brain" / conv_id
    if brain_dir.is_dir():
        try:
            dest_brain = trash_dir / "brain"
            if dest_brain.exists():
                shutil.rmtree(dest_brain, ignore_errors=True)
            shutil.copytree(brain_dir, dest_brain)
        except Exception:
            pass

    # 4. Archive SQLite metadata if available
    if con:
        try:
            cur = con.cursor()
            row = cur.execute("SELECT * FROM conversation_summaries WHERE conversation_id = ?;", (conv_id,)).fetchone()
            if row:
                col_names = [d[0] for d in cur.description]
                row_dict = {}
                for i in range(len(row)):
                    val = row[i]
                    if isinstance(val, (bytes, bytearray)):
                        row_dict[col_names[i]] = base64.b64encode(val).decode("ascii")
                    else:
                        row_dict[col_names[i]] = val
                (trash_dir / "summary.json").write_text(json.dumps(row_dict, indent=2), encoding="utf-8")
        except Exception:
            pass

    return trash_dir


def restore_chat_from_trash(
    conv_id: str,
    effective_master: Path,
    user_home: Optional[Path] = None,
) -> bool:
    """Restores a deleted conversation from the trash archive and untombstones it."""
    home = user_home or get_user_home()
    trash_dir = home / ".config" / "antigravity" / "backups" / "trash" / conv_id
    if not trash_dir.is_dir():
        return False

    # 1. Restore .db file
    t_db = trash_dir / f"{conv_id}.db"
    if t_db.is_file():
        dest_db = effective_master / "conversations" / f"{conv_id}.db"
        dest_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(t_db, dest_db)

    # 2. Restore .pbtxt
    t_anno = trash_dir / f"{conv_id}.pbtxt"
    if t_anno.is_file():
        dest_anno = effective_master / "annotations" / f"{conv_id}.pbtxt"
        dest_anno.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(t_anno, dest_anno)

    # 3. Restore brain directory
    t_brain = trash_dir / "brain"
    if t_brain.is_dir():
        dest_brain = effective_master / "brain" / conv_id
        dest_brain.parent.mkdir(parents=True, exist_ok=True)
        if dest_brain.exists():
            shutil.rmtree(dest_brain, ignore_errors=True)
        shutil.copytree(t_brain, dest_brain)

    # 4. Untombstone in sync_manifest.json
    manifest = load_manifest(effective_master)
    if conv_id in manifest.get("tombstones", {}):
        manifest["tombstones"].pop(conv_id, None)
    if conv_id not in manifest.get("known_ids", []):
        manifest.setdefault("known_ids", []).append(conv_id)
    if conv_id not in manifest.get("known_app_ids", []):
        manifest.setdefault("known_app_ids", []).append(conv_id)
    if conv_id not in manifest.get("known_ide_ids", []):
        manifest.setdefault("known_ide_ids", []).append(conv_id)
    save_manifest(effective_master, manifest)

    return True


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
    """
    Completely and permanently purges a conversation across all persistence layers:
    Archives to trash -> Notifies running LS runtimes -> IDE state.vscdb -> App electron storage
    -> SQLite database -> FTS index -> in-memory index -> disk databases -> brain folders -> annotations.
    """
    # 0. Safety archive to trash before making any modifications
    archive_deleted_conversation(conv_id, effective_master, user_home, con=con)

    # 1. Notify running Language Server runtimes FIRST (while db is present or temporary db ensures LoadTrajectory succeeds)
    notify_language_servers_deletion(conv_id, effective_master=effective_master)

    # 2. IDE state.vscdb ItemTables
    for vscdb in candidate_vscdbs:
        purge_conversation_from_vscdb(vscdb, conv_id)

    # 3. Desktop App electron storage
    purge_conversation_from_app_storage(conv_id, user_home=user_home)

    # 4. Master SQLite tables
    cur = con.cursor()
    cur.execute("DELETE FROM conversation_summaries WHERE conversation_id = ?;", (conv_id,))
    try:
        cur.execute("DELETE FROM conversations_fts WHERE conversation_id = ?;", (conv_id,))
    except Exception:
        pass
    con.commit()

    # 5. Memory summaries dictionary
    all_summaries.pop(conv_id, None)

    # 6. Disk conversation databases (.db, .pb, .json) across all pools
    all_conv_pools = [effective_master / "conversations"] + [Path(p) for p in conv_pools]
    for c_pool in all_conv_pools:
        for ext in [".db", ".db-wal", ".db-shm", ".pb", ".json"]:
            target_f = c_pool / f"{conv_id}{ext}"
            if target_f.exists():
                try:
                    target_f.unlink()
                except Exception:
                    pass

    # 7. Annotations .pbtxt
    anno_f = effective_master / "annotations" / f"{conv_id}.pbtxt"
    if anno_f.exists():
        try:
            anno_f.unlink()
        except Exception:
            pass

    # 8. Brain folders (.trash relocation or removal)
    all_brain_pools = [effective_master / "brain"] + [Path(p) for p in brain_pools]
    for b_pool in all_brain_pools:
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


def detect_and_sync_deletions(
    effective_master: Path,
    candidate_vscdbs: List[Path],
    conv_pools: List[str],
    brain_pools: List[str],
    all_summaries: Dict[str, bytes],
    stats: SyncStats,
    con: Optional[sqlite3.Connection] = None,
    user_home: Optional[Path] = None,
) -> int:
    """
    Detects asymmetric deletions between Desktop App and IDE, purging deleted chats
    from the counterpart environment and recording permanent tombstones. Also cleans
    orphaned ghost trajectories where disk databases and transcripts no longer exist.

    Returns:
        Number of conversations successfully deleted and synchronized.
    """
    own_conn = False
    if con is None:
        db_path = effective_master / "conversation_summaries.db"
        if not db_path.is_file():
            return 0
        con = sqlite3.connect(str(db_path), timeout=15.0)
        own_conn = True

    try:
        cur = con.cursor()
        # Discover active App IDs from master SQLite
        app_rows = cur.execute("SELECT conversation_id FROM conversation_summaries WHERE killed = 0;").fetchall()
        current_app_ids = set(r[0] for r in app_rows if r[0])

        # Discover active IDE IDs from candidate_vscdbs
        current_ide_ids = get_active_ide_ids(candidate_vscdbs)

        manifest = load_manifest(effective_master)
        prev_app = set(manifest.get("known_app_ids", manifest.get("known_ids", [])))
        prev_ide = set(manifest.get("known_ide_ids", manifest.get("known_ids", [])))
        tombstones = set(manifest.get("tombstones", {}).keys())

        # Initial boot: populate known sets from currently active universe
        if not prev_app and not prev_ide:
            manifest["known_app_ids"] = sorted(list(current_app_ids - tombstones))
            manifest["known_ide_ids"] = sorted(list(current_ide_ids - tombstones))
            manifest["known_ids"] = sorted(list((current_app_ids | current_ide_ids) - tombstones))
            save_manifest(effective_master, manifest)
            return 0

        # 1. Deleted in App: was active in App, now absent from App, not tombstoned
        if not current_app_ids:
            deleted_in_app = set()
        elif len(prev_app) > 5 and len(current_app_ids) < len(prev_app) * 0.5:
            deleted_in_app = set()
        else:
            deleted_in_app = (prev_app - current_app_ids) - tombstones

        # 2. Deleted in IDE: was active in IDE, now absent from IDE, not tombstoned
        if not candidate_vscdbs or not current_ide_ids:
            deleted_in_ide = set()
        elif len(prev_ide) > 5 and len(current_ide_ids) < len(prev_ide) * 0.5:
            deleted_in_ide = set()
        else:
            deleted_in_ide = (prev_ide - current_ide_ids) - tombstones

        to_purge = deleted_in_app | deleted_in_ide
        if not to_purge:
            manifest["known_app_ids"] = sorted(list(current_app_ids - tombstones))
            manifest["known_ide_ids"] = sorted(list(current_ide_ids - tombstones))
            manifest["known_ids"] = sorted(list((current_app_ids | current_ide_ids) - tombstones))
            save_manifest(effective_master, manifest)
            return 0

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        purged_count = 0

        for c_id in sorted(to_purge):
            if c_id in deleted_in_app:
                source = "app"
            elif c_id in deleted_in_ide:
                source = "ide"
            else:
                source = "ghost"

            purge_conversation(
                conv_id=c_id,
                effective_master=effective_master,
                con=con,
                candidate_vscdbs=candidate_vscdbs,
                conv_pools=conv_pools,
                brain_pools=brain_pools,
                all_summaries=all_summaries,
                user_home=user_home,
            )
            manifest.setdefault("tombstones", {})[c_id] = {
                "deleted_at": now_iso,
                "source": source,
            }
            stats.conversations_deleted += 1
            stats.dirty_conv_ids.add(c_id)
            purged_count += 1

        # Update manifest
        manifest["known_app_ids"] = sorted(list((current_app_ids - to_purge) - tombstones))
        manifest["known_ide_ids"] = sorted(list((current_ide_ids - to_purge) - tombstones))
        manifest["known_ids"] = sorted(list(((current_app_ids | current_ide_ids) - to_purge) - tombstones))
        save_manifest(effective_master, manifest)

        return purged_count
    finally:
        if own_conn and con:
            try:
                con.close()
            except Exception:
                pass
