"""
Data models for Antigravity AI performance and latency benchmarking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
    networks: List[NetworkMetric] = field(default_factory=list)
    context: ContextMetric = field(default_factory=ContextMetric)
    processes: List[ProcessMetric] = field(default_factory=list)
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
            "networks": [m.__dict__ for m in self.networks],
            "context": self.context.__dict__,
            "processes": [p.__dict__ for p in self.processes],
        }
