"""
Data models for Antigravity AI performance and latency benchmarking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models_system import (
    AccountQuotaMetric,
    EnvironmentMetric,
    PromptTestMetric,
    QuotaBucket,
)


@dataclass
class NetworkMetric:
    host: str
    dns_ipv4_ms: Optional[float] = None
    dns_ipv6_ms: Optional[float] = None
    tcp_ipv4_ms: Optional[float] = None
    tcp_ipv6_ms: Optional[float] = None
    tls_handshake_ms: Optional[float] = None
    alpn_protocol: str = "unknown"
    ipv6_blackhole: bool = False
    proxy_used: Optional[str] = None
    fake_ip_detected: bool = False
    resolved_ip: Optional[str] = None
    doh_ms: Optional[float] = None
    real_ip: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ContextMetric:
    mcp_servers: int = 0
    mcp_eager_tools: int = 0
    mcp_lazy_tools: int = 0
    total_mcp_tools: int = 0
    active_skills: int = 0
    active_rules: int = 0
    estimated_prompt_tokens: int = 0


@dataclass
class ProcessMetric:
    pid: int
    client_type: str
    gomaxprocs: int = 4
    rss_mb: float = 0.0
    port: int = 0
    loopback_ping_ms: Optional[float] = None
    flags: List[str] = field(default_factory=list)


@dataclass
class BenchmarkReport:
    env: EnvironmentMetric = field(default_factory=EnvironmentMetric)
    accounts: List[AccountQuotaMetric] = field(default_factory=list)
    networks: List[NetworkMetric] = field(default_factory=list)
    context: ContextMetric = field(default_factory=ContextMetric)
    processes: List[ProcessMetric] = field(default_factory=list)
    prompt_test: Optional[PromptTestMetric] = None
    speed_tier: str = "OPTIMAL"
    estimated_ttft_sec: str = "2s - 4s"
    bottlenecks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speed_tier": self.speed_tier,
            "estimated_ttft": self.estimated_ttft_sec,
            "bottlenecks": self.bottlenecks,
            "recommendations": self.recommendations,
            "environment": self.env.__dict__,
            "accounts": [a.__dict__ for a in self.accounts],
            "networks": [m.__dict__ for m in self.networks],
            "context": self.context.__dict__,
            "processes": [p.__dict__ for p in self.processes],
            "prompt_test": self.prompt_test.__dict__ if self.prompt_test else None,
        }
