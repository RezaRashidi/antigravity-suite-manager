"""
CLI Entry Point for Antigravity History Synchronization and Daemon Service.
"""

from __future__ import annotations

import json
import sys
from typing import List, Optional

from antigravity_suite.cli.args import build_parser
from antigravity_suite.cli.handlers import (
    handle_list_backups,
    handle_list_trash,
    handle_restore_backup,
    handle_restore_chat,
    print_report,
)
from antigravity_suite.history.lock import ProcessLock
from antigravity_suite.history.merger import merge_histories
from antigravity_suite.history.watcher import watch_mode

__all__ = [
    "build_parser",
    "print_report",
    "handle_list_backups",
    "handle_restore_backup",
    "handle_list_trash",
    "handle_restore_chat",
    "main",
]


def main(argv: Optional[List[str]] = None) -> int:
    """CLI runner main entry point."""
    args = build_parser().parse_args(argv)

    if args.list_backups:
        return handle_list_backups()
    if args.restore:
        return handle_restore_backup(args.restore)
    if args.list_trash:
        return handle_list_trash()
    if args.restore_chat:
        return handle_restore_chat(args.restore_chat, master_gemini=args.master)
    if args.watch:
        lock = ProcessLock("antigravity_history_watcher")
        if not lock.acquire(non_blocking=True):
            if not args.quiet:
                print("[Antigravity Watcher] Another watcher daemon is already running. Exiting.", file=sys.stderr)
            return 0
        try:
            watch_mode(master_gemini=args.master)
            return 0
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            print(f"Fatal daemon error: {e}", file=sys.stderr)
            return 1
        finally:
            lock.release()

    sync_lock = ProcessLock("antigravity_history_sync")
    if not sync_lock.acquire(non_blocking=bool(args.quiet), timeout_sec=0.0 if args.quiet else 10.0):
        if not args.quiet:
            print("[Antigravity History] Another merge is in progress. Exiting.", file=sys.stderr)
        return 0

    try:
        stats = merge_histories(
            master_gemini=args.master,
            source_dir=args.source,
            target_dir=args.target,
            quiet=args.quiet,
            force_rebuild=args.force,
            skip_backup=args.no_backup,
        )
        if args.json:
            print(json.dumps(stats.to_dict(), indent=2))
        elif not args.quiet:
            print_report(stats.to_dict())
        return 0
    except Exception as e:
        print(f"Error during synchronization: {e}", file=sys.stderr)
        return 1
    finally:
        sync_lock.release()


if __name__ == "__main__":
    sys.exit(main())
