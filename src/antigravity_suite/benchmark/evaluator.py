"""
Latency evaluator and bottleneck diagnosis engine.
"""

from __future__ import annotations

from typing import List, Tuple

from .models import ContextMetric, NetworkMetric, ProcessMetric


def evaluate_bottlenecks(
    networks: List[NetworkMetric],
    context: ContextMetric,
    processes: List[ProcessMetric],
) -> Tuple[str, str, List[str], List[str]]:
    bottlenecks: List[str] = []
    recommendations: List[str] = []
    base_latency_sec = 2.0

    for net in networks:
        if net.ipv6_blackhole:
            bottlenecks.append(
                f"IPv6 Blackhole on {net.host}: connection stalled or timed out."
            )
            recommendations.append(
                "Disable IPv6 via 'sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1' "
                "to save 5-9 seconds per request."
            )
            base_latency_sec += 7.0
        elif net.tcp_ipv4_ms and net.tcp_ipv4_ms > 250:
            bottlenecks.append(
                f"High network ping to {net.host}: {net.tcp_ipv4_ms} ms."
            )
            base_latency_sec += 1.5

        if net.tls_handshake_ms and net.tls_handshake_ms > 400:
            bottlenecks.append(
                f"Slow TLS handshake with {net.host}: {net.tls_handshake_ms} ms."
            )
            recommendations.append(
                "Verify proxy keep-alive settings to prevent repeated TLS handshakes."
            )
            base_latency_sec += 1.0

    if context.estimated_prompt_tokens > 15000:
        bottlenecks.append(
            f"Prompt prefill bloat: ~{context.estimated_prompt_tokens} tokens "
            f"from {context.total_mcp_tools} MCP tools and {context.active_skills} skills."
        )
        recommendations.append(
            "Convert eager MCP tools to lazy-loaded mode or disable unused MCP servers."
        )
        base_latency_sec += (context.estimated_prompt_tokens / 10000.0) * 1.5

    for proc in processes:
        if proc.loopback_ping_ms and proc.loopback_ping_ms > 50:
            bottlenecks.append(
                f"Language Server PID {proc.pid} loopback lag: {proc.loopback_ping_ms} ms."
            )

    if base_latency_sec <= 4.0:
        tier = "OPTIMAL"
        ttft = "1.5s - 3.5s"
    elif base_latency_sec <= 8.0:
        tier = "MODERATE"
        ttft = "4.0s - 7.5s"
    else:
        tier = "BOTTLENECKED"
        ttft = f"{int(base_latency_sec)}s - {int(base_latency_sec + 4)}s"

    return tier, ttft, bottlenecks, recommendations
