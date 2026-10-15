"""
CLI Entry Point for Antigravity History Synchronization and Daemon Service.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from antigravity.config import DEFAULT_CONFIG
from antigravity.history.merger import merge_histories
from antigravity.history.watcher import watch_mode


def build_parser() -> argparse.ArgumentParser:
    """Builds the argument parser for antigravity-merge-history CLI."""
    parser = argparse.ArgumentParser(
        description="Unified History Synchronization and Real-Time Daemon for Antigravity App and IDE.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--master",
        default=str(DEFAULT_CONFIG.master_app_dir),
        help=f"Master Antigravity app directory (default: {DEFAULT_CONFIG.master_app_dir})",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Legacy source directory path (optional)",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Optional target Antigravity profile directory to synchronize into",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run continuously in the background as a real-time file-system synchronization daemon",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuilding conversation SQLite databases from transcript logs even if existing",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output and banner table",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output synchronization telemetry report as structured JSON",
    )
    return parser


def print_report(stats: dict) -> None:
    """Prints the formatted human-readable synchronization report banner."""
    print("=" * 88)
    print("                       Antigravity History Synchronization Report                       ")
    print("=" * 88)
    print(f"  • History Pools Scanned:      {stats['conv_stores_scanned']} conv stores, {stats['brain_stores_scanned']} brain stores")
    print(f"  • DB Files Merged:            {stats['db_files_merged']} new databases imported")
    print(f"  • Brain Folders Merged:       {stats['brain_folders_merged']} new project folders imported")
    print(f"  • Databases Reconstructed:    {stats['databases_reconstructed']} SQLite databases built from transcript logs")
    print(f"  • Summaries Backfilled:       {stats['summaries_backfilled']} newly indexed conversations")
    print(f"  • Conversations Updated:      {stats['conversations_updated']} existing chats refreshed with authentic titles")
    print(f"  • IDE state.vscdb Ingested:   {stats['ide_state_ingested']} conversations from IDE")
    print(f"  • Total Active History:       {stats['total_active_history']} conversations synchronized")
    print(f"  • Target Stores Updated:      Desktop App, IDE state.vscdb, SQLite DB, Protobuf Files")
    print("=" * 88)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI runner main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.watch:
        try:
            watch_mode(master_gemini=args.master)
            return 0
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            print(f"Fatal daemon error: {e}", file=sys.stderr)
            return 1

    try:
        stats = merge_histories(
            master_gemini=args.master,
            source_dir=args.source,
            target_dir=args.target,
            quiet=args.quiet,
            force_rebuild=args.force,
        )

        if args.json:
            print(json.dumps(stats.to_dict(), indent=2))
        elif not args.quiet:
            print_report(stats.to_dict())

        return 0
    except Exception as e:
        print(f"Error during synchronization: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
