"""
System, account, and prompt test data models for benchmarking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EnvironmentMetric:
    os_name: str = ""
    kernel: str = ""
    cpu_model: str = ""
    cpu_cores: int = 0
    load_avg: str = ""
    ram_total_mb: float = 0.0
    ram_avail_mb: float = 0.0
    app_version: str = "unknown"
    ide_version: str = "unknown"
    active_proxies: Dict[str, str] = field(default_factory=dict)


@dataclass
class QuotaBucket:
    name: str
    window: str
    remaining_fraction: float
    reset_time: str


@dataclass
class AccountQuotaMetric:
    email: str = ""
    name: str = ""
    tier: str = "unknown"
    plan_name: str = ""
    region_code: str = ""
    buckets: List[QuotaBucket] = field(default_factory=list)
    source: str = "none"
    error: Optional[str] = None


@dataclass
class PromptTestMetric:
    prompt_text: str = ""
    latency_ms: Optional[float] = None
    success: bool = False
    output_preview: str = ""
    error: Optional[str] = None
