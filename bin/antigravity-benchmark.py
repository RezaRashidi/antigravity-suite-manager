#!/usr/bin/env python3
"""
Antigravity AI Response Speed & Latency Benchmark CLI.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_SRC_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "src"))
if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from antigravity_suite.benchmark import format_report, run_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark and diagnose Antigravity AI response speed and latency bottlenecks."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw benchmark results as JSON",
    )
    parser.add_argument(
        "--skip-network",
        action="store_true",
        help="Skip external network and TLS benchmark checks",
    )
    parser.add_argument(
        "--host",
        action="append",
        dest="hosts",
        help="Custom Cloud Code PA host(s) to benchmark",
    )

    args = parser.parse_args()
    report = run_benchmark(skip_network=args.skip_network, hosts=args.hosts)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report(report))

    return 0 if report.speed_tier != "BOTTLENECKED" else 1


if __name__ == "__main__":
    sys.exit(main())
