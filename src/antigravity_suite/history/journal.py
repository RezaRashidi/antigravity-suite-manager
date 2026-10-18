"""
History Synchronization Debug Journal.

Maintains a comprehensive, human-readable and structured decision journal
recording every action, evaluated candidate, title selection rationale,
partition assignment, and store mutation for each individual conversation.
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class SyncJournal:
    """Records fine-grained debugging decisions and actions per conversation."""

    def __init__(self, journal_path: Optional[Path] = None) -> None:
        if journal_path is None:
            gemini_dir = os.environ.get("GEMINI_DIR") or os.path.expanduser("~/.gemini")
            self.journal_path = Path(gemini_dir) / "antigravity" / "history_sync_journal.log"
        else:
            self.journal_path = Path(journal_path)

    def record_chat_action(
        self,
        conv_id: str,
        action: str,
        title: str,
        title_source: str,
        old_title: Optional[str],
        partition: str,
        partition_reason: str,
        step_count: int,
        mutations: List[str],
        candidates: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Appends a clear diagnostic decision entry to the debug journal."""
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        title_disp = f"'{old_title}' -> '{title}'" if old_title and old_title != title else f"'{title}'"
        muts_str = ",".join(mutations) if mutations else "none"

        line = (
            f"[{ts}] [{conv_id[:8]}] {action:<18} | "
            f"Title: {title_disp:<40} (via {title_source}) | "
            f"Partition: {partition:<15} ({partition_reason}) | "
            f"Steps: {step_count:<3} | Stores: [{muts_str}]\n"
        )

        try:
            if not self.journal_path.parent.is_dir():
                self.journal_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.journal_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass


_JOURNAL: Optional[SyncJournal] = None


def get_sync_journal(journal_path: Optional[Path] = None) -> SyncJournal:
    """Returns singleton SyncJournal instance."""
    global _JOURNAL
    if _JOURNAL is None or journal_path is not None:
        _JOURNAL = SyncJournal(journal_path)
    return _JOURNAL
