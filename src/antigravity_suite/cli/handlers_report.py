"""
CLI Command Handlers for History Reports and Backups.
"""

from __future__ import annotations

import sys
from antigravity_suite.history.backup import HistoryBackupManager


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
    if HistoryBackupManager.restore_backup(backup_id):
        print(f"✓ Backup '{backup_id}' successfully restored!")
        print("  - conversation_summaries.db, protobuf indexes, and IDE state restored.")
        return 0
    print(f"✗ Failed to restore backup '{backup_id}'. Check ID or permissions.", file=sys.stderr)
    return 1
