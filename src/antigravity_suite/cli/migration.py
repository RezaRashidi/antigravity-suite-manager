"""
CLI parser and command router for Antigravity migration tool.
"""

from __future__ import annotations

import argparse
import sys
from antigravity_suite.migration.cleanup import (
    delete_all_data,
    delete_app_data,
    delete_history_data,
    delete_ide_data,
)
from antigravity_suite.migration.export_all import export_all
from antigravity_suite.migration.export_history import export_history
from antigravity_suite.migration.export_suite import export_suite
from antigravity_suite.migration.import_all import import_all
from antigravity_suite.migration.import_history import import_history
from antigravity_suite.migration.import_suite import import_suite
from antigravity_suite.migration.restore import restore_backup
from antigravity_suite.migration.safety import create_safety_backup, list_all_backups


def build_parser() -> argparse.ArgumentParser:
    """Builds CLI subcommands and options for migration tool."""
    parser = argparse.ArgumentParser(description="Antigravity Suite Cross-System Migration & Backup Tool")
    sub = parser.add_subparsers(dest="command", help="Available subcommands")

    sub.add_parser("export-history", help="Export conversation history").add_argument("output", nargs="?", default=None)
    sub.add_parser("import-history", help="Import conversation history").add_argument("archive")
    sub.add_parser("export-suite", help="Export suite configs").add_argument("output", nargs="?", default=None)
    sub.add_parser("import-suite", help="Import suite configs").add_argument("archive")
    sub.add_parser("export-all", help="Export both history and suite").add_argument("output", nargs="?", default=None)
    sub.add_parser("import-all", help="Auto-detect and import archive").add_argument("archive")
    sub.add_parser("list-backups", help="List available local snapshots and backups")

    p_cr_b = sub.add_parser("create-backup", help="Create an instant safety snapshot")
    p_cr_b.add_argument("--category", default="all", choices=["app", "ide", "history", "suite", "all"])
    p_cr_b.add_argument("--label", default="manual")

    p_clean = sub.add_parser("clean-data", help="Clean or purge Antigravity application data")
    p_clean.add_argument("target", choices=["app", "ide", "history", "all"])
    p_clean.add_argument("--no-backup", action="store_true", help="Skip pre-cleanup safety backup")
    p_clean.add_argument("-y", "--yes", action="store_true", help="Bypass interactive confirmation")

    sub.add_parser("restore-backup", help="Restore state from backup").add_argument("backup_path")
    return parser


def handle_clean_data(parsed: argparse.Namespace) -> None:
    target = parsed.target
    backup = not parsed.no_backup
    if not parsed.yes:
        conf = input(f"Are you sure you want to clean/delete '{target}' data? [y/N]: ").strip().lower()
        if conf not in ["y", "yes"]:
            print("Operation aborted.")
            return

    if target == "app":
        delete_app_data(backup=backup)
    elif target == "ide":
        delete_ide_data(backup=backup)
    elif target == "history":
        delete_history_data(backup=backup)
    elif target == "all":
        delete_all_data(backup=backup)


def main(args: list[str] | None = None) -> int:
    """Entry point for migration CLI execution."""
    parser = build_parser()
    parsed = parser.parse_args(args)
    if not parsed.command:
        parser.print_help()
        return 0

    actions = {
        "export-history": lambda: export_history(parsed.output),
        "import-history": lambda: import_history(parsed.archive),
        "export-suite": lambda: export_suite(parsed.output),
        "import-suite": lambda: import_suite(parsed.archive),
        "export-all": lambda: export_all(parsed.output),
        "import-all": lambda: import_all(parsed.archive),
        "list-backups": lambda: list_all_backups(),
        "create-backup": lambda: create_safety_backup(category=parsed.category, label=parsed.label),
        "clean-data": lambda: handle_clean_data(parsed),
        "restore-backup": lambda: restore_backup(parsed.backup_path),
    }
    actions[parsed.command]()
    return 0
