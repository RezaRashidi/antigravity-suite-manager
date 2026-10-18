"""
CLI Argument Parser for antigravity-merge-history.
"""

from __future__ import annotations

import argparse
from antigravity_suite.config import DEFAULT_CONFIG


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
    parser.add_argument(
        "--list-backups",
        action="store_true",
        help="List available automated history backups and exit",
    )
    parser.add_argument(
        "--restore",
        metavar="BACKUP_ID",
        default=None,
        help="Restore history databases and IDE state from a specific backup ID or path and exit",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip automatic pre-merge backup snapshot",
    )
    parser.add_argument(
        "--restore-chat",
        metavar="CONVERSATION_ID",
        default=None,
        help="Restore a deleted conversation from the trash archive and exit",
    )
    parser.add_argument(
        "--list-trash",
        action="store_true",
        help="List conversations currently stored in the trash archive and exit",
    )
    return parser
