"""Process supervisor and status checker for the local model proxy daemon."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from antigravity_suite.config_paths import get_user_home

DEFAULT_PROXY_PORT = 50999


def get_proxy_pid_path() -> Path:
    custom = os.environ.get("ANTIGRAVITY_PROXY_PID_PATH")
    p = Path(custom).resolve() if custom else get_user_home() / ".config/antigravity/models_proxy.pid"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_proxy_state_path() -> Path:
    return get_user_home() / ".gemini/antigravity/.ide-proxy/state.json"


def get_proxy_pid() -> Optional[int]:
    custom = os.environ.get("ANTIGRAVITY_PROXY_PID_PATH")
    pid_file = get_proxy_pid_path()
    if custom or pid_file.is_file():
        if not pid_file.is_file():
            return None
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError):
            pid_file.unlink(missing_ok=True)
            return None
    state_file = get_proxy_state_path()
    if state_file.is_file():
        try:
            pid = json.loads(state_file.read_text()).get("pid")
            if pid and isinstance(pid, int):
                os.kill(pid, 0)
                return pid
        except (ValueError, OSError):
            pass
    return None


def is_proxy_running(port: int = DEFAULT_PROXY_PORT) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/_addon/health", timeout=0.5) as r:
            if r.status == 200:
                return True
    except Exception:
        pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def get_proxy_status(port: int = DEFAULT_PROXY_PORT) -> Dict[str, Any]:
    pid = get_proxy_pid()
    return {"running": is_proxy_running(port) or (pid is not None), "pid": pid, "port": port}


def start_proxy_daemon(port: int = DEFAULT_PROXY_PORT, cmd: Optional[List[str]] = None) -> bool:
    if is_proxy_running(port):
        return True
    c = cmd
    if not c:
        v = Path(__file__).resolve().parent.parent.parent.parent / "vendor/antigravity-model-proxy/scripts/desktop-service.mjs"
        if v.is_file():
            c = ["node", str(v), "start", "--port", str(port)]
    if c:
        proc = subprocess.Popen(c, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        get_proxy_pid_path().write_text(str(proc.pid))
    return is_proxy_running(port)


def stop_proxy_daemon(port: int = DEFAULT_PROXY_PORT) -> bool:
    pid = get_proxy_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    get_proxy_pid_path().unlink(missing_ok=True)
    if is_proxy_running(port):
        pass
    return not is_proxy_running(port)
