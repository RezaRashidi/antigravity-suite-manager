"""
Benchmark orchestrator and runner.
"""

from __future__ import annotations

from typing import List, Optional

from .context import benchmark_context
from .evaluator import evaluate_bottlenecks
from .models import BenchmarkReport
from .network import run_network_benchmarks
from .system import benchmark_processes


def run_benchmark(
    skip_network: bool = False,
    hosts: Optional[List[str]] = None,
) -> BenchmarkReport:
    report = BenchmarkReport()
    if not skip_network:
        report.networks = run_network_benchmarks(hosts=hosts)

    report.context = benchmark_context()
    report.processes = benchmark_processes()

    tier, ttft, bottlenecks, recs = evaluate_bottlenecks(
        report.networks, report.context, report.processes
    )
    report.speed_tier = tier
    report.estimated_ttft_sec = ttft
    report.bottlenecks = bottlenecks
    report.recommendations = recs
    return report
