"""
Bi-directional Conversation Deletion and Tombstone Synchronization Engine.

Tracks synchronized conversation lifecycles across Antigravity Desktop App and IDE.
When a conversation is deleted in either environment (Desktop App or IDE),
this engine guarantees atomic, permanent deletion from both sides, preventing
resurrection by pool mergers, reconstruction engines, or state serializers.
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
            "version": 1,
            "known_ids": [],
            "tombstones": {},
            "last_synced_at": "",
        }
    try:
        with open(m_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"version": 1, "known_ids": [], "tombstones": {}, "last_synced_at": ""}
            data.setdefault("version", 1)
            data.setdefault("known_ids", [])
            data.setdefault("tombstones", {})
            return data
    except Exception:
        return {
            "version": 1,
            "known_ids": [],
            "tombstones": {},
            "last_synced_at": "",
        }


def save_manifest(effective_master: Path, manifest: Dict[str, Any]) -> None:
    """Atomically saves the synchronization manifest to disk."""
    m_path = get_manifest_path(effective_master)
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


def notify_language_servers_deletion(conv_id: str) -> None:
    """
    Invokes loopback ConnectRPC on all running Language Servers to immediately
    evict the deleted conversation from memory and broadcast deletion to frontends.
    """
    servers = find_running_language_servers()
    ctx = ssl._create_unverified_context()
    payload = json.dumps({"cascadeId": conv_id}).encode("utf-8")

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
            # 1. JetboxDeleteSummary (Desktop App Hub)
            url_jetbox = f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/JetboxDeleteSummary"
            try:
                req = urllib.request.Request(url_jetbox, data=payload, headers=headers)
                with urllib.request.urlopen(req, context=ctx, timeout=1.0):
                    pass
            except Exception:
                pass

            # 2. DeleteCascadeTrajectory (Both IDE and Hub)
            url_del = f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/DeleteCascadeTrajectory"
            try:
                req = urllib.request.Request(url_del, data=payload, headers=headers)
                with urllib.request.urlopen(req, context=ctx, timeout=1.0):
                    pass
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

        # 1. trajectorySummaries
        for key in ["antigravityUnifiedStateSync.trajectorySummaries", "antigravityUnifiedStateSync"]:
            row = cur.execute("SELECT value FROM ItemTable WHERE key = ?;", (key,)).fetchone()
            if row and row[0]:
                try:
                    v_bin = base64.b64decode(row[0])
                    entries = extract_entries_from_proto(v_bin)
                    if conv_id in entries:
                        entries.pop(conv_id, None)
                        # Re-encode remaining
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


def purge_conversation(
    conv_id: str,
    effective_master: Path,
    con: sqlite3.Connection,
    candidate_vscdbs: List[Path],
    conv_pools: List[str],
    brain_pools: List[str],
    all_summaries: Dict[str, bytes],
) -> None:
    """
    Completely and permanently purges a conversation across all persistence layers:
    SQLite database, FTS index, memory dictionary, disk databases, brain folders,
    annotations, IDE state.vscdb tables, and running Language Server runtimes.
    """
    # 1. Master SQLite tables
    cur = con.cursor()
    cur.execute("DELETE FROM conversation_summaries WHERE conversation_id = ?;", (conv_id,))
    try:
        cur.execute("DELETE FROM conversations_fts WHERE conversation_id = ?;", (conv_id,))
    except Exception:
        pass
    con.commit()

    # 2. Memory summaries dictionary
    all_summaries.pop(conv_id, None)

    # 3. Disk conversation databases (.db, .pb, .json) across all pools
    all_conv_pools = [effective_master / "conversations"] + [Path(p) for p in conv_pools]
    for c_pool in all_conv_pools:
        for ext in [".db", ".db-wal", ".db-shm", ".pb", ".json"]:
            target_f = c_pool / f"{conv_id}{ext}"
            if target_f.exists():
                try:
                    target_f.unlink()
                except Exception:
                    pass

    # 4. Annotations .pbtxt
    anno_f = effective_master / "annotations" / f"{conv_id}.pbtxt"
    if anno_f.exists():
        try:
            anno_f.unlink()
        except Exception:
            pass

    # 5. Brain folders (.trash relocation or removal)
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

    # 6. IDE state.vscdb ItemTables
    for vscdb in candidate_vscdbs:
        purge_conversation_from_vscdb(vscdb, conv_id)

    # 7. Running Language Server runtimes (App and IDE)
    notify_language_servers_deletion(conv_id)


def detect_and_sync_deletions(
    effective_master: Path,
    con: sqlite3.Connection,
    candidate_vscdbs: List[Path],
    conv_pools: List[str],
    brain_pools: List[str],
    all_summaries: Dict[str, bytes],
    stats: SyncStats,
) -> int:
    """
    Detects asymmetric deletions between Desktop App and IDE, purging deleted chats
    from the counterpart environment and recording permanent tombstones.

    Returns:
        Number of conversations successfully deleted and synchronized.
    """
    cur = con.cursor()
    # Discover active App IDs from master SQLite
    app_rows = cur.execute("SELECT conversation_id FROM conversation_summaries WHERE killed = 0;").fetchall()
    app_ids = set(r[0] for r in app_rows if r[0])

    # Discover active IDE IDs from candidate_vscdbs
    ide_ids = get_active_ide_ids(candidate_vscdbs)

    manifest = load_manifest(effective_master)
    prev_known = set(manifest.get("known_ids", []))
    tombstones = set(manifest.get("tombstones", {}).keys())

    # Initial boot: populate known_ids from currently active universe
    if not prev_known:
        initial_universe = (app_ids | ide_ids) - tombstones
        manifest["known_ids"] = sorted(list(initial_universe))
        save_manifest(effective_master, manifest)
        return 0

    # Detect deletions:
    # 1. Deleted in App: was previously known, still present in IDE, but absent from App
    deleted_in_app = (prev_known & ide_ids) - app_ids - tombstones

    # 2. Deleted in IDE: was previously known, still present in App, but absent from IDE
    deleted_in_ide = (prev_known & app_ids) - ide_ids - tombstones

    to_purge = deleted_in_app | deleted_in_ide
    if not to_purge:
        # Update known_ids with any freshly created conversations
        manifest["known_ids"] = sorted(list((app_ids | ide_ids) - tombstones))
        save_manifest(effective_master, manifest)
        return 0

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    purged_count = 0

    for c_id in sorted(to_purge):
        source = "app" if c_id in deleted_in_app else "ide"
        purge_conversation(
            conv_id=c_id,
            effective_master=effective_master,
            con=con,
            candidate_vscdbs=candidate_vscdbs,
            conv_pools=conv_pools,
            brain_pools=brain_pools,
            all_summaries=all_summaries,
        )
        manifest.setdefault("tombstones", {})[c_id] = {
            "deleted_at": now_iso,
            "source": source,
        }
        stats.conversations_deleted += 1
        stats.dirty_conv_ids.add(c_id)
        purged_count += 1

    # Update manifest known_ids
    new_known = (app_ids | ide_ids) - to_purge - tombstones
    manifest["known_ids"] = sorted(list(new_known))
    save_manifest(effective_master, manifest)

    return purged_count
