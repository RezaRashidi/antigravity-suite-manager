"""
Latency evaluator and bottleneck diagnosis engine.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .models import ContextMetric, NetworkMetric, ProcessMetric
from .models_system import AccountQuotaMetric, PromptTestMetric


def _add_rec(recs: List[str], text: str) -> None:
    if text not in recs:
        recs.append(text)


def evaluate_bottlenecks(
    networks: List[NetworkMetric],
    context: ContextMetric,
    processes: List[ProcessMetric],
    accounts: Optional[List[AccountQuotaMetric]] = None,
    prompt_test: Optional[PromptTestMetric] = None,
) -> Tuple[str, str, List[str], List[str]]:
    bottlenecks: List[str] = []
    recs: List[str] = []
    base_latency = 2.0

    for net in networks:
        if net.ipv6_blackhole:
            bottlenecks.append(f"IPv6 Blackhole on {net.host}: connection stalled.")
            _add_rec(recs, "Disable IPv6 via sysctl to avoid 5-9s timeout.")
            base_latency += 7.0
        elif net.tcp_ipv4_ms and net.tcp_ipv4_ms > 250:
            bottlenecks.append(f"High network ping to {net.host}: {net.tcp_ipv4_ms} ms.")
            base_latency += 1.5

        if net.tls_handshake_ms and net.tls_handshake_ms > 400:
            bottlenecks.append(f"Slow TLS handshake with {net.host}: {net.tls_handshake_ms} ms.")
            _add_rec(recs, "Verify proxy keep-alive and connection pooling to avoid repeated TLS handshakes.")
            base_latency += 1.0

    if context.estimated_prompt_tokens > 15000:
        bottlenecks.append(
            f"Prompt prefill bloat: ~{context.estimated_prompt_tokens} tokens "
            f"({context.total_mcp_tools} tools, {context.active_skills} skills)."
        )
        _add_rec(recs, "Convert eager MCP tools to lazy-loaded mode.")
        base_latency += (context.estimated_prompt_tokens / 10000.0) * 1.5

    for acc in (accounts or []):
        for b in acc.buckets:
            if b.window == "weekly" and b.remaining_fraction < 0.25:
                bottlenecks.append(
                    f"Low weekly quota on {acc.email or 'Account'}: {b.remaining_fraction * 100:.1f}% remaining. "
                    "Google Cloud Code deprioritizes and rate-limits low-quota tiers."
                )
                _add_rec(recs, "Switch active account or wait for weekly quota reset window.")
                base_latency += 2.5

    if prompt_test and prompt_test.latency_ms and prompt_test.latency_ms > 2500:
        bottlenecks.append(f"Live prompt latency elevated: {prompt_test.latency_ms:.1f} ms.")

    if base_latency <= 4.0:
        tier, ttft = "OPTIMAL", "1.5s - 3.5s"
    elif base_latency <= 8.0:
        tier, ttft = "MODERATE", "4.0s - 7.5s"
    else:
        tier, ttft = "BOTTLENECKED", f"{int(base_latency)}s - {int(base_latency + 4)}s"

    return tier, ttft, bottlenecks, recs
