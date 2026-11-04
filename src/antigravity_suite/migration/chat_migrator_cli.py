"""
CLI runner for One-Shot Legacy Chat Migrator (v2.5.5 -> v2.6.0).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from antigravity_suite.migration.chat_migrator import (
    check_ide_version,
    plan_migration,
    run_migration,
)


def build_migrator_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="One-Shot Legacy Chat Migrator (Antigravity IDE v2.5.5 -> v2.6.0+).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dry-run", action="store_true", help="Inspect versions and chat counts without migrating")
    p.add_argument("--force", action="store_true", help="Force re-migration of all legacy trajectories")
    p.add_argument("--no-backup", action="store_true", help="Skip pre-migration snapshot backup")
    p.add_argument("--json", action="store_true", help="Output migration results as structured JSON")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_migrator_parser().parse_args(argv)
    ver_info = check_ide_version()
    plan = plan_migration()

    if args.dry_run:
        if args.json:
            print(json.dumps({"version_info": ver_info, "plan": plan}, indent=2))
        else:
            print("================================================================")
            print("       Antigravity Chat Migrator: v2.5.5 -> v2.6.0 (Dry Run)    ")
            print("================================================================")
            print(f"[Version Check] Detected IDE Version: {ver_info['version']}")
            status_str = "Compatible (>= v2.6.0)" if ver_info["is_v260_plus"] else "Warning (< v2.6.0)"
            print(f"[Version Check] Unified Database Target: {status_str}")
            print(f"[Legacy Storage] Legacy v2.5.5 chats found: {plan['legacy_total']}")
            print(f"[Target Storage] Already in v2.6.0 database: {plan['already_in_v260']}")
            print(f"[Migration Plan] Chats requiring migration: {plan['to_migrate_count']}")
            print("================================================================")
        return 0

    if not args.json:
        print("================================================================")
        print("       Antigravity Chat Migrator: v2.5.5 -> v2.6.0              ")
        print("================================================================")
        print(f"[Version Check] Detected IDE Version: {ver_info['version']}")
        print(f"[Legacy Storage] Legacy v2.5.5 chats found: {plan['legacy_total']}")
        print(f"[Target Storage] Already in v2.6.0 database: {plan['already_in_v260']}")
        print(f"[Migration Plan] Chats queued for migration: {plan['to_migrate_count']}")

    if plan["to_migrate_count"] == 0 and not args.force:
        if args.json:
            print(json.dumps({"status": "noop", "message": "All chats present in v2.6.0", "plan": plan}, indent=2))
        else:
            print("\n[OK] All legacy chats are already present in v2.6.0 database.")
            print("[OK] No migration required.")
            print("================================================================")
        return 0

    if not args.json:
        print(f"\n[Migrating] Transferring {plan['to_migrate_count']} chats into v2.6.0 storage...")

    res = run_migration(force=args.force, skip_backup=args.no_backup)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"[Success] Migrated {res['newly_migrated']} legacy chats.")
        print(f"[Success] Total conversations in v2.6.0: {res['total_v260_chats']}")
        print("================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
