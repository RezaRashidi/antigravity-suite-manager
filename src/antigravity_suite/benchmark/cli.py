"""
Command-line interface for Antigravity AI benchmark.
"""

from __future__ import annotations

import argparse
import json
from typing import List, Optional

from .reporter import format_report
from .runner import run_benchmark


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark and diagnose Antigravity AI response speed and latency bottlenecks."
    )
    parser.add_argument("--json", action="store_true", help="Output raw results as JSON")
    parser.add_argument("--skip-network", action="store_true", help="Skip external network and TLS checks")
    parser.add_argument("--skip-prompt", action="store_true", help="Skip live prompt turnaround test")
    parser.add_argument("--host", action="append", dest="hosts", help="Custom host(s) to benchmark")

    args = parser.parse_args(argv)
    report = run_benchmark(
        skip_network=args.skip_network,
        skip_prompt=args.skip_prompt,
        hosts=args.hosts,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report(report))

    return 0 if report.speed_tier != "BOTTLENECKED" else 1
