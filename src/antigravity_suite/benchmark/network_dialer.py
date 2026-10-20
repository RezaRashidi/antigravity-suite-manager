"""
Low-level socket dialer and TLS handshake timer for benchmark.
"""

from __future__ import annotations

import socket
import ssl
import time
from typing import Optional, Tuple


def measure_tcp(
    host: str, port: int, family: socket.AddressFamily, timeout: float = 3.0
) -> Tuple[Optional[float], Optional[str]]:
    start = time.perf_counter()
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        elapsed = (time.perf_counter() - start) * 1000.0
        sock.close()
        return round(elapsed, 2), None
    except socket.timeout:
        sock.close()
        return None, "TIMEOUT"
    except Exception as exc:
        sock.close()
        return None, str(exc)


def measure_tls(
    host: str, port: int = 443, timeout: float = 5.0
) -> Tuple[Optional[float], str, Optional[str]]:
    ctx = ssl.create_default_context()
    ctx.set_alpn_protocols(["h2", "http/1.1"])
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        start = time.perf_counter()
        tls_sock = ctx.wrap_socket(sock, server_hostname=host)
        elapsed = (time.perf_counter() - start) * 1000.0
        proto = tls_sock.selected_alpn_protocol() or "http/1.1"
        tls_sock.close()
        return round(elapsed, 2), proto, None
    except Exception as exc:
        sock.close()
        return None, "none", str(exc)
