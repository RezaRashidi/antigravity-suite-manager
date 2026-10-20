"""
Network latency and endpoint benchmark for Cloud Code PA backends.
"""

from __future__ import annotations

import os
import socket
import time
from typing import List

from .models import NetworkMetric
from .network_dialer import measure_tcp, measure_tls

TARGET_HOSTS = [
    "daily-cloudcode-pa.googleapis.com",
    "cloudcode-pa.googleapis.com",
]


def resolve_dns(host: str, family: socket.AddressFamily) -> tuple[float | None, str | None]:
    start = time.perf_counter()
    try:
        results = socket.getaddrinfo(host, 443, family, socket.SOCK_STREAM)
        elapsed = (time.perf_counter() - start) * 1000.0
        ip = results[0][4][0] if results else None
        return round(elapsed, 2), ip
    except Exception:
        return None, None


def benchmark_endpoint(host: str) -> NetworkMetric:
    metric = NetworkMetric(host=host)
    metric.proxy_used = (
        os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("all_proxy")
    )
    metric.dns_ipv4_ms, ip4 = resolve_dns(host, socket.AF_INET)
    metric.dns_ipv6_ms, ip6 = resolve_dns(host, socket.AF_INET6)

    if ip4:
        metric.tcp_ipv4_ms, _ = measure_tcp(ip4, 443, socket.AF_INET, timeout=3.0)
    if ip6:
        metric.tcp_ipv6_ms, err6 = measure_tcp(ip6, 443, socket.AF_INET6, timeout=3.0)
        if err6 == "TIMEOUT" or (metric.tcp_ipv6_ms is None and err6):
            metric.ipv6_blackhole = True

    tls_ms, alpn, tls_err = measure_tls(host, 443, timeout=5.0)
    metric.tls_handshake_ms = tls_ms
    metric.alpn_protocol = alpn
    if tls_err:
        metric.error = tls_err
    return metric


def run_network_benchmarks(hosts: List[str] | None = None) -> List[NetworkMetric]:
    targets = hosts or TARGET_HOSTS
    return [benchmark_endpoint(h) for h in targets]
