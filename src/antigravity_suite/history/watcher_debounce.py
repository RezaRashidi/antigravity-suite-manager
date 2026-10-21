"""
Watcher Event Debouncing and File Relevance Filter.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple


def is_relevant_event(ev_path: str) -> bool:
    """Checks whether an event path is relevant for triggering history synchronization."""
    norm = ev_path.lower()
    if "workspacestorage" in norm:
        return False
    base = os.path.basename(ev_path)
    if (
        not base
        or base.startswith("conversation_summaries")
        or base.startswith(".")
        or base.endswith(".pbtxt")
        or base.endswith(".pb")
        or base.endswith("-wal")
        or base.endswith("-shm")
        or base.endswith(".tmp")
        or base.endswith(".log")
        or base.endswith(".lock")
        or base == "transcript_full.jsonl"
        or base == "app_storage.json"
    ):
        return False
    if base.endswith(".vscdb"):
        return "globalstorage" in norm
    return (
        base.endswith(".db")
        or base.endswith(".jsonl")
        or base.endswith(".md")
    )


class DebounceTracker:
    """Tracks change burst frequency and settles quiet periods before triggering sync."""

    def __init__(self, debounce_seconds: float = 3.0) -> None:
        self.debounce_seconds = debounce_seconds
        self.first_change_time: Optional[float] = None
        self.last_change_time: Optional[float] = None
        self.burst_count = 0
        self.pending_file: Optional[str] = None

    def record_change(self, file_path: str, now: float) -> None:
        if self.first_change_time is None:
            self.first_change_time = now
            self.burst_count = 1
        else:
            self.burst_count += 1
        self.last_change_time = now
        self.pending_file = file_path

    def should_trigger(self, now: float) -> Tuple[bool, str]:
        if self.first_change_time is None or self.last_change_time is None:
            return False, ""
        quiet_duration = now - self.last_change_time
        total_duration = now - self.first_change_time
        required_quiet = self.debounce_seconds if self.burst_count <= 1 else min(self.debounce_seconds * 2.0, 6.0)

        if quiet_duration >= required_quiet:
            return True, f"quiet period settled ({quiet_duration:.1f}s >= {required_quiet:.1f}s, bursts={self.burst_count})"
        if total_duration >= 45.0:
            return True, f"hard deadline ceiling reached ({total_duration:.1f}s >= 45.0s, bursts={self.burst_count})"
        return False, ""

    def reset(self) -> None:
        self.first_change_time = None
        self.last_change_time = None
        self.burst_count = 0
        self.pending_file = None
