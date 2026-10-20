"""
Benchmark orchestrator and runner.
"""

from __future__ import annotations

from typing import List, Optional

from .account import collect_accounts_and_quotas
from .context import benchmark_context
from .environment import collect_environment
from .evaluator import evaluate_bottlenecks
from .models import BenchmarkReport
from .network import run_network_benchmarks
from .prompt_test import run_prompt_test
from .system import benchmark_processes


def run_benchmark(
    skip_network: bool = False,
    skip_prompt: bool = False,
    hosts: Optional[List[str]] = None,
) -> BenchmarkReport:
    report = BenchmarkReport()
    report.env = collect_environment()
    report.accounts = collect_accounts_and_quotas()

    if not skip_network:
        report.networks = run_network_benchmarks(hosts=hosts)

    report.context = benchmark_context()
    report.processes = benchmark_processes()

    if not skip_prompt:
        report.prompt_test = run_prompt_test()

    tier, ttft, bottlenecks, recs = evaluate_bottlenecks(
        report.networks,
        report.context,
        report.processes,
        accounts=report.accounts,
        prompt_test=report.prompt_test,
    )
    report.speed_tier = tier
    report.estimated_ttft_sec = ttft
    report.bottlenecks = bottlenecks
    report.recommendations = recs
    return report
