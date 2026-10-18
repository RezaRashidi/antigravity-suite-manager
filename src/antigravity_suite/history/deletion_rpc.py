"""
Language Server Discovery and ConnectRPC Deletion Notification.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import ssl
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def find_running_language_servers() -> List[Dict[str, Any]]:
    """Discovers all active Language Server processes, loopback ports, and CSRF tokens."""
    servers: List[Dict[str, Any]] = []
    pid_ports: Dict[int, List[int]] = {}
    try:
        ss_out = subprocess.run(["ss", "-tulpn"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=2.0).stdout
        for line in ss_out.splitlines():
            if "127.0.0.1:" in line and "pid=" in line:
                m_port, m_pid = re.search(r"127\.0\.0\.1:(\d+)", line), re.search(r"pid=(\d+)", line)
                if m_port and m_pid:
                    pid_ports.setdefault(int(m_pid.group(1)), []).append(int(m_port.group(1)))
    except Exception:
        pass

    for pid, ports in pid_ports.items():
        cmdline_file = f"/proc/{pid}/cmdline"
        if os.path.exists(cmdline_file):
            try:
                with open(cmdline_file, "rb") as f:
                    cmd_str = f.read().decode("utf-8", errors="ignore").replace("\x00", " ")
                if "language_server" in cmd_str:
                    csrf = re.search(r"--csrf_token[=\s]+([a-f0-9-]+)", cmd_str)
                    app_data = re.search(r"--app_data_dir[=\s]+([^\s]+)", cmd_str)
                    subclient = re.search(r"--subclient_type[=\s]+([^\s]+)", cmd_str)
                    servers.append({
                        "pid": pid, "ports": ports, "csrf": csrf.group(1) if csrf else None,
                        "app_data_dir": app_data.group(1) if app_data else None,
                        "subclient_type": subclient.group(1) if subclient else None,
                    })
            except Exception:
                pass
    return servers


def _call_rpc(port: int, method: str, csrf_token: str, payload: bytes, ctx: ssl.SSLContext) -> bool:
    headers = {"Content-Type": "application/json", "x-codeium-csrf-token": csrf_token, "Connect-Protocol-Version": "1"}
    try:
        req = urllib.request.Request(f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/{method}", data=payload, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=1.5):
            return True
    except Exception as e:
        if "WRONG_VERSION_NUMBER" in str(e) or "SSL" in str(type(e).__name__):
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/{method}", data=payload, headers=headers)
                with urllib.request.urlopen(req, timeout=1.5):
                    return True
            except Exception:
                pass
    return False


def notify_language_servers_deletion(conv_id: str, effective_master: Optional[Path] = None) -> None:
    """Invokes loopback ConnectRPC on running Language Servers to evict deleted conversation."""
    servers = find_running_language_servers()
    if not servers:
        return
    temp_db: Optional[Path] = None
    if effective_master and not (effective_master / "conversations" / f"{conv_id}.db").exists():
        temp_db = effective_master / "conversations" / f"{conv_id}.db"
        try:
            temp_db.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(temp_db)) as t_con:
                t_con.executescript("CREATE TABLE IF NOT EXISTS steps (idx INTEGER PRIMARY KEY, step_type INTEGER DEFAULT 0, status INTEGER DEFAULT 0, has_subtrajectory NUMERIC DEFAULT false, metadata BLOB, error_details BLOB, permissions BLOB, task_details BLOB, render_info BLOB, step_payload BLOB, step_format INTEGER DEFAULT 0); CREATE TABLE IF NOT EXISTS trajectory_meta (trajectory_id TEXT PRIMARY KEY, cascade_id TEXT, trajectory_type INTEGER, source INTEGER); CREATE TABLE IF NOT EXISTS trajectory_metadata_blob (id TEXT PRIMARY KEY DEFAULT 'main', data BLOB);")
        except Exception:
            temp_db = None

    ctx = ssl._create_unverified_context()
    payload = json.dumps({"cascadeId": conv_id}).encode("utf-8")
    try:
        for s in servers:
            csrf = s.get("csrf")
            if csrf:
                for port in s.get("ports", []):
                    for m in ["DeleteCascadeTrajectory", "JetboxDeleteSummary", "DeleteCascadeMemory"]:
                        _call_rpc(port, m, csrf, payload, ctx)
    finally:
        if temp_db and temp_db.exists():
            try:
                temp_db.unlink()
            except Exception:
                pass
