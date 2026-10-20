"""
Network latency and endpoint benchmark for Cloud Code PA backends.
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.request
from typing import List

from .models import NetworkMetric
from .network_dialer import measure_tcp, measure_tls

TARGET_HOSTS = ["daily-cloudcode-pa.googleapis.com", "cloudcode-pa.googleapis.com"]


def resolve_dns(host: str, family: socket.AddressFamily) -> tuple[float | None, str | None]:
    start = time.perf_counter()
    try:
        results = socket.getaddrinfo(host, 443, family, socket.SOCK_STREAM)
        elapsed = (time.perf_counter() - start) * 1000.0
        return round(elapsed, 2), results[0][4][0] if results else None
    except Exception:
        return None, None


def resolve_doh(host: str) -> tuple[float | None, str | None]:
    start = time.perf_counter()
    url = f"https://dns.google/resolve?name={host}&type=A"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Antigravity/1.0", "Accept": "application/dns-json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            elapsed = (time.perf_counter() - start) * 1000.0
            data = json.loads(resp.read().decode("utf-8"))
            for ans in data.get("Answer", []):
                if ans.get("type") == 1:
                    return round(elapsed, 2), ans.get("data")
    except Exception:
        pass
    return None, None


def benchmark_endpoint(host: str) -> NetworkMetric:
    metric = NetworkMetric(host=host)
    metric.proxy_used = os.environ.get("https_proxy") or os.environ.get("all_proxy")
    metric.dns_ipv4_ms, ip4 = resolve_dns(host, socket.AF_INET)
    metric.dns_ipv6_ms, ip6 = resolve_dns(host, socket.AF_INET6)
    metric.doh_ms, metric.real_ip = resolve_doh(host)

    if ip4:
        metric.resolved_ip = ip4
        metric.tcp_ipv4_ms, _ = measure_tcp(ip4, 443, socket.AF_INET, timeout=3.0)
        is_synth = ip4.startswith(("198.18.", "198.19.", "127."))
        is_sub = metric.tcp_ipv4_ms is not None and metric.tcp_ipv4_ms < 1.0
        if is_synth or is_sub:
            metric.fake_ip_detected = True

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
    return [benchmark_endpoint(h) for h in (hosts or TARGET_HOSTS)]
