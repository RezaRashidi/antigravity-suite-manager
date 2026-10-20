"""
Language server RPC and token extraction for account quotas.
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


def find_ls_ports_and_csrf() -> List[Tuple[int, int, str]]:
    try:
        out = subprocess.check_output(["pgrep", "-a", "language_server"], text=True)
    except Exception:
        return []

    try:
        ss_out = subprocess.check_output(["ss", "-tlpn"], text=True)
    except Exception:
        ss_out = ""

    results: List[Tuple[int, int, str]] = []
    for line in out.strip().split("\n"):
        parts = line.split(None, 1)
        if len(parts) < 2: continue
        pid = int(parts[0])
        csrf_m = re.search(r"--csrf_token(?:=|\s+)([0-9a-fA-F-]+)", parts[1])
        if not csrf_m: continue
        csrf = csrf_m.group(1)

        for pline in ss_out.split("\n"):
            if f"pid={pid}," in pline:
                pm = re.search(r"127\.0\.0\.1:(\d+)", pline)
                if pm:
                    results.append((pid, int(pm.group(1)), csrf))
    return results


def call_ls_rpc(port: int, csrf: str, method: str, payload: bytes = b"{}") -> Optional[Dict[str, Any]]:
    url = f"http://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/{method}"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "x-codeium-csrf-token": csrf},
    )
    try:
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))
    except Exception:
        return None


def call_cloudcode_rpc(token: str, rpc_method: str) -> Optional[Dict[str, Any]]:
    url = f"https://cloudcode-pa.googleapis.com/v1internal:{rpc_method}"
    req = urllib.request.Request(
        url,
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Antigravity/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            return json.loads(resp.read().decode("utf-8", "ignore"))
    except Exception:
        return None
