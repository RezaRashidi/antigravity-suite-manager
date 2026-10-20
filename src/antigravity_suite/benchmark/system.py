"""
Local Language Server process inspector and loopback ConnectRPC benchmark.
"""

from __future__ import annotations

import os
import re
import socket
import time
from typing import List

from .models import ProcessMetric


def ping_port(port: int, timeout: float = 1.0) -> float | None:
    if port <= 0:
        return None
    start = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(("127.0.0.1", port))
        sock.close()
        return round((time.perf_counter() - start) * 1000.0, 2)
    except Exception:
        sock.close()
        return None


def parse_proc(pid: int, cmdline: str) -> ProcessMetric:
    client_type = "unknown"
    if "--subclient_type" in cmdline:
        m = re.search(r"--subclient_type\s+([^\s]+)", cmdline)
        if m:
            client_type = m.group(1)

    gomaxprocs = 4
    m_procs = re.search(r"-limit_go_max_procs=(\d+)", cmdline)
    if m_procs:
        gomaxprocs = int(m_procs.group(1))

    port = 0
    m_port = re.search(r"--https_server_port\s+(\d+)", cmdline)
    if m_port:
        port = int(m_port.group(1))
    if port == 0:
        m_lsp = re.search(r"--extension_server_port\s+(\d+)", cmdline)
        if m_lsp:
            port = int(m_lsp.group(1))

    rss_mb = 0.0
    statm_path = f"/proc/{pid}/statm"
    if os.path.isfile(statm_path):
        try:
            with open(statm_path, "r") as f:
                parts = f.read().split()
                rss_pages = int(parts[1])
                rss_mb = round((rss_pages * 4096) / (1024 * 1024), 1)
        except Exception:
            pass

    ping_ms = ping_port(port) if port > 0 else None
    return ProcessMetric(
        pid=pid,
        client_type=client_type,
        gomaxprocs=gomaxprocs,
        rss_mb=rss_mb,
        port=port,
        loopback_ping_ms=ping_ms,
    )


def benchmark_processes() -> List[ProcessMetric]:
    metrics: List[ProcessMetric] = []
    if not os.path.isdir("/proc"):
        return metrics

    for pid_str in os.listdir("/proc"):
        if not pid_str.isdigit():
            continue
        cmd_path = f"/proc/{pid_str}/cmdline"
        if not os.path.isfile(cmd_path):
            continue
        try:
            with open(cmd_path, "rb") as f:
                cmd = f.read().replace(b"\x00", b" ").decode("utf-8", "ignore")
                if "language_server" in cmd:
                    metrics.append(parse_proc(int(pid_str), cmd))
        except Exception:
            continue
    return sorted(metrics, key=lambda x: x.pid)
