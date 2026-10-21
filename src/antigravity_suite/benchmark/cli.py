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
    parser.add_argument("--all-steps", action="store_true", help="Display all step intervals for each message")
    parser.add_argument("--messages", type=int, default=10, help="Number of recent messages to inspect (default: 10)")
    parser.add_argument("--transcript", type=str, default=None, help="Path to transcript.jsonl file")
    parser.add_argument("--host", action="append", dest="hosts", help="Custom host(s) to benchmark")

    args = parser.parse_args(argv)
    report = run_benchmark(
        skip_network=args.skip_network,
        skip_prompt=args.skip_prompt,
        hosts=args.hosts,
        messages_count=args.messages,
        transcript_path=args.transcript,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report(report, all_steps=args.all_steps))

    return 0 if report.speed_tier != "BOTTLENECKED" else 1
