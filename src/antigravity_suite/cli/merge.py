"""
CLI Entry Point for Antigravity History Synchronization and Daemon Service.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from antigravity_suite.config import DEFAULT_CONFIG, get_user_home
from antigravity_suite.history.backup import HistoryBackupManager
from antigravity_suite.history.merger import merge_histories
from antigravity_suite.history.watcher import watch_mode


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


def print_report(stats: dict) -> None:
    """Prints the formatted human-readable synchronization report banner."""
    print("=" * 88)
    print("                       Antigravity History Synchronization Report                       ")
    print("=" * 88)
    if stats.get("backup_id"):
        print(f"  • Backup Snapshot Created:    {stats['backup_id']}")
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


def handle_list_backups() -> int:
    """Lists existing backup snapshots in a formatted table."""
    backups = HistoryBackupManager.list_backups()
    if not backups:
        print("No historical backups found in ~/.config/antigravity/backups/history.")
        return 0

    print("=" * 88)
    print("                       Antigravity History Backups Archive                       ")
    print("=" * 88)
    print(f" {'BACKUP ID':<36} | {'TIMESTAMP':<22} | {'VSCDB':<5} | {'FILES'}")
    print("-" * 88)
    for b in backups:
        files_str = ", ".join(b.files) if b.files else "none"
        print(f" {b.backup_id:<36} | {b.timestamp[:19]:<22} | {b.vscdb_entries_count:<5} | {files_str}")
    print("=" * 88)
    print(f"Total backups stored: {len(backups)}")
    print("To restore a backup, run: antigravity-merge-history --restore <BACKUP_ID>")
    return 0


def handle_restore_backup(backup_id: str) -> int:
    """Restores system state from the specified backup snapshot."""
    print(f"Initiating restoration from backup: {backup_id}...")
    success = HistoryBackupManager.restore_backup(backup_id)
    if success:
        print(f"✓ Backup '{backup_id}' successfully restored!")
        print("  - conversation_summaries.db, protobuf indexes, and IDE state restored.")
        return 0
    else:
        print(f"✗ Failed to restore backup '{backup_id}'. Check ID or permissions.", file=sys.stderr)
        return 1


def handle_list_trash(user_home: Optional[Path] = None) -> int:
    """Lists conversations currently stored in the safety trash archive."""
    home = user_home or get_user_home()
    trash_root = home / ".config" / "antigravity" / "backups" / "trash"
    if not trash_root.is_dir():
        print("Trash archive is empty.")
        return 0
    items = sorted(trash_root.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not items:
        print("Trash archive is empty.")
        return 0
    print("=" * 88)
    print("                      Antigravity Conversation Trash Archive                      ")
    print("=" * 88)
    print(f" {'CONVERSATION ID':<38} | {'TITLE'}")
    print("-" * 88)
    for it in items:
        if not it.is_dir():
            continue
        title = "Conversation"
        sum_f = it / "summary.json"
        if sum_f.is_file():
            try:
                s_data = json.loads(sum_f.read_text(encoding="utf-8"))
                title = s_data.get("title") or title
            except Exception:
                pass
        print(f" {it.name:<38} | {title}")
    print("=" * 88)
    print("To restore a chat, run: antigravity-merge-history --restore-chat <ID>")
    return 0


def handle_restore_chat(conv_id: str, master_gemini: Optional[Path] = None, user_home: Optional[Path] = None) -> int:
    """Restores a deleted conversation from trash archive and un-tombstones it."""
    home = user_home or get_user_home()
    effective_master = Path(master_gemini).resolve() if master_gemini else (home / ".gemini" / "antigravity")
    from antigravity_suite.history.deletion import restore_chat_from_trash
    success = restore_chat_from_trash(conv_id, effective_master=effective_master, user_home=home)
    if success:
        print(f"✓ Successfully restored conversation '{conv_id}' from trash archive!")
        print("  - Database, annotations, and brain folder restored. Tombstone removed.")
        print("  - Running sync cycle to propagate back to App and IDE...")
        merge_histories(master_gemini=effective_master, user_home=home, quiet=True)
        return 0
    else:
        print(f"✗ Conversation '{conv_id}' not found in trash archive.", file=sys.stderr)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """CLI runner main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_backups:
        return handle_list_backups()

    if args.restore:
        return handle_restore_backup(args.restore)

    if args.list_trash:
        return handle_list_trash()

    if args.restore_chat:
        return handle_restore_chat(args.restore_chat, master_gemini=args.master)

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


if __name__ == "__main__":
    sys.exit(main())
