"""
CLI Command Handlers for History Safety Trash Management.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from antigravity_suite.config import get_user_home


def handle_list_trash(user_home: Optional[Path] = None) -> int:
    """Lists conversations currently stored in the safety trash archive."""
    trash_root = (user_home or get_user_home()) / ".config" / "antigravity" / "backups" / "trash"
    items = sorted([p for p in trash_root.glob("*") if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True) if trash_root.is_dir() else []
    if not items:
        print("Trash archive is empty.")
        return 0
    print("=" * 88)
    print("                      Antigravity Conversation Trash Archive                      ")
    print("=" * 88)
    print(f" {'CONVERSATION ID':<38} | {'TITLE'}")
    print("-" * 88)
    for it in items:
        title = "Conversation"
        sum_f = it / "summary.json"
        if sum_f.is_file():
            try:
                title = json.loads(sum_f.read_text(encoding="utf-8")).get("title") or title
            except Exception:
                pass
        print(f" {it.name:<38} | {title}")
    print("=" * 88)
    print("To restore a chat, run: antigravity-merge-history --restore-chat <ID>")
    return 0


def handle_restore_chat(conv_id: str, master_gemini: Optional[Path] = None, user_home: Optional[Path] = None) -> int:
    """Restores a deleted conversation from trash archive and un-tombstones it."""
    from antigravity_suite.history.deletion import restore_chat_from_trash
    from antigravity_suite.history.merger import merge_histories

    home = user_home or get_user_home()
    master = Path(master_gemini).resolve() if master_gemini else (home / ".gemini" / "antigravity")
    if restore_chat_from_trash(conv_id, effective_master=master, user_home=home):
        print(f"✓ Successfully restored conversation '{conv_id}' from trash archive!")
        print("  - Database, annotations, and brain folder restored. Tombstone removed.")
        print("  - Running sync cycle to propagate back to App and IDE...")
        merge_histories(master_gemini=master, user_home=home, quiet=True)
        return 0
    print(f"✗ Conversation '{conv_id}' not found in trash archive.", file=sys.stderr)
    return 1
