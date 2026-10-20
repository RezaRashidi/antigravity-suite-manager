"""
Terminal formatter and report generator for Antigravity speed benchmarks.
"""

from __future__ import annotations

from .models import BenchmarkReport
from .reporter_sections import (
    format_account_section,
    format_env_section,
    format_prompt_test_section,
)

_GREEN, _YELLOW, _RED, _CYAN = "\033[92m", "\033[93m", "\033[91m", "\033[96m"
_BOLD, _RESET = "\033[1m", "\033[0m"


def format_report(report: BenchmarkReport) -> str:
    lines = [f"{_BOLD}{_CYAN}=== Antigravity AI Response Speed & Latency Benchmark ==={_RESET}\n"]
    tier_col = _GREEN if report.speed_tier == "OPTIMAL" else (_YELLOW if report.speed_tier == "MODERATE" else _RED)
    lines.append(f"Speed Rating: {tier_col}{_BOLD}{report.speed_tier}{_RESET} (Estimated TTFT: {report.estimated_ttft_sec})\n")

    lines.append(f"{_BOLD}1. Network & Protocol Latencies:{_RESET}")
    for net in report.networks:
        ip6_str = f"{_RED}TIMEOUT{_RESET}" if net.ipv6_blackhole else (f"{net.tcp_ipv6_ms} ms" if net.tcp_ipv6_ms else "n/a")
        fake_tag = f" {_YELLOW}[TUN Loopback]{_RESET}" if net.fake_ip_detected else ""
        ip4_str = f"{net.tcp_ipv4_ms} ms{fake_tag}" if net.tcp_ipv4_ms else "n/a"
        tls_str = f"{net.tls_handshake_ms} ms" if net.tls_handshake_ms else "error"
        doh_tag = f" | DoH: {net.real_ip} ({net.doh_ms} ms)" if net.real_ip else ""
        lines.append(f"  - {net.host:36} | IPv4: {ip4_str:8} | IPv6: {ip6_str:8} | TLS ({net.alpn_protocol}): {tls_str}{doh_tag}")
        if net.proxy_used:
            lines.append(f"    Proxy: {net.proxy_used}")

    lines.extend(format_account_section(report.accounts))
    lines.extend(format_prompt_test_section(report.prompt_test))

    lines.append(f"\n{_BOLD}Local Context & System Prompt Bloat:{_RESET}")
    c = report.context
    lines.append(f"  - Active MCP Servers : {c.mcp_servers} ({c.total_mcp_tools} tools [{c.mcp_eager_tools} eager, {c.mcp_lazy_tools} lazy])")
    lines.append(f"  - Installed Skills   : {c.active_skills}")
    lines.append(f"  - Active Rules       : {c.active_rules}")
    lines.append(f"  - Est. Prompt Tokens : ~{c.estimated_prompt_tokens} tokens before chat input")

    lines.append(f"\n{_BOLD}Running Language Servers:{_RESET}")
    if not report.processes:
        lines.append("  (No active language_server processes detected)")
    for p in report.processes:
        ping = f"{p.loopback_ping_ms} ms" if p.loopback_ping_ms else "n/a"
        lines.append(f"  - PID {p.pid:6} [{p.client_type:4}] | Port: {p.port:5} | GOMAXPROCS: {p.gomaxprocs} | RSS: {p.rss_mb:6.1f} MB | Ping: {ping}")

    lines.extend(format_env_section(report.env))

    if report.bottlenecks:
        lines.append(f"\n{_RED}{_BOLD}Identified Bottlenecks:{_RESET}")
        for b in report.bottlenecks:
            lines.append(f"  [!] {b}")

    if report.recommendations:
        lines.append(f"\n{_GREEN}{_BOLD}Actionable Recommendations:{_RESET}")
        for r in report.recommendations:
            lines.append(f"  [>] {r}")

    return "\n".join(lines)
