"""Service supervisor for the multi-account background proxy daemon."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, Optional

DEFAULT_PROXY_PORT = 41999


def get_pid_file() -> Path:
    p = Path.home() / ".config" / "antigravity" / "accounts"
    p.mkdir(parents=True, exist_ok=True)
    return p / "proxy.pid"


def is_proxy_running(port: int = DEFAULT_PROXY_PORT) -> bool:
    try:
        url = f"http://127.0.0.1:{port}/healthz"
        with urllib.request.urlopen(url, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("status") == "ok"
    except Exception:
        return False


def start_proxy_daemon(port: int = DEFAULT_PROXY_PORT) -> bool:
    if is_proxy_running(port):
        return True
    pid_file = get_pid_file()
    cmd = [
        sys.executable,
        "-m",
        "antigravity_suite.multi_account.cli",
        "serve",
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    with open(pid_file, "w") as f:
        f.write(str(proc.pid))
    for _ in range(20):
        time.sleep(0.1)
        if is_proxy_running(port):
            return True
    return False


def stop_proxy_daemon() -> bool:
    pid_file = get_pid_file()
    if pid_file.is_file():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            pid_file.unlink()
            return True
        except Exception:
            pass
    return False
