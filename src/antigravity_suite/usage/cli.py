"""CLI entrypoint for `manage-antigravity.sh usage`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from .render import render_usage_report
from .scanner import scan_usage


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="manage-antigravity.sh usage",
        description="Read-only token usage, Cache Hit Rate, and USD cost report from Antigravity transcripts.",
    )
    parser.add_argument("--days", type=str, default=None, help="Filter window in days (e.g. 7, 30, or 'all')")
    parser.add_argument("--account", type=str, default=None, help="Filter by account email substring (or 'unbound')")
    parser.add_argument("--model", type=str, default=None, help="Filter by model name substring")
    parser.add_argument("--json", action="store_true", help="Output structured JSON")
    parser.add_argument("--refresh-prices", action="store_true", help="Force refresh pricing table from models.dev")
    parser.add_argument("--no-network", action="store_true", help="Use cached/fallback pricing without network fetch")
    parser.add_argument("--brain-dir", type=str, default=None, help="Override brain directory path")

    args = parser.parse_args(argv)
    days_int: Optional[int] = None
    if args.days and str(args.days).strip().lower() != "all":
        try:
            days_int = max(1, int(args.days))
        except ValueError:
            parser.error(f"Invalid --days value: {args.days}")

    report = scan_usage(
        days=days_int,
        account_filter=args.account,
        model_filter=args.model,
        brain_dir=Path(args.brain_dir) if args.brain_dir else None,
        refresh_prices=args.refresh_prices,
        allow_network=not args.no_network,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_usage_report(report))
    return 0
