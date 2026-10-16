"""
Real-Time File Watcher and Synchronization Daemon for Antigravity History.

Monitors conversation directories across all instances using inotify or
timestamp polling with intelligent event debouncing and clean POSIX signal termination.
"""

from __future__ import annotations

import glob
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

from antigravity_suite.config import DEFAULT_CONFIG, get_user_home
from antigravity_suite.history.discovery import discover_all_history_sources
from antigravity_suite.history.merger import merge_histories


def watch_mode(
    master_gemini: Optional[Union[str, Path]] = None,
    user_home: Optional[Union[str, Path]] = None,
    debounce_seconds: float = 3.0,
) -> None:
    """
    Watches conversation and brain directories for modifications.
    Executes incremental history merges whenever active files are updated.
    """
    home = Path(user_home).resolve() if user_home else get_user_home()
    effective_master = (
        Path(master_gemini).resolve()
        if master_gemini
        else Path(os.environ.get("ANTIGRAVITY_APP_DIR", home / ".gemini" / "antigravity")).resolve()
    )

    running = True

    def _sig_handler(signum: int, frame: object) -> None:
        nonlocal running
        print(f"\n[Antigravity Watcher] Received signal {signum}, stopping gracefully...", flush=True)
        running = False

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    print(f"[Antigravity Watcher] Initializing real-time history synchronization daemon...", flush=True)
    # Initial synchronization pass
    try:
        merge_histories(effective_master, quiet=True, user_home=home)
    except Exception as e:
        print(f"[Antigravity Watcher] Warning: Initial merge encountered error: {e}", flush=True)

    print(f"[Antigravity Watcher] Actively monitoring conversation directories for modifications...", flush=True)

    def _get_mtime_snapshot(dirs: List[str]) -> Dict[str, float]:
        snapshot: Dict[str, float] = {}
        for d in dirs:
            if not os.path.isdir(d):
                continue
            for pattern in ["*.db", "*.pb", "conversation_summaries.db", "conversation_summaries.db-wal"]:
                for f in glob.glob(os.path.join(d, pattern)):
                    try:
                        snapshot[f] = os.path.getmtime(f)
                    except Exception:
                        pass
        return snapshot

    last_merge_time = time.time()
    last_snapshot: Dict[str, float] = {}

    while running:
        try:
            conv_pools, _, _ = discover_all_history_sources(user_home=home)
            watch_dirs = list(set([str(effective_master / "conversations")] + conv_pools))
            current_snapshot = _get_mtime_snapshot(watch_dirs)

            has_changes = False
            for f, mtime in current_snapshot.items():
                if f not in last_snapshot or last_snapshot[f] < mtime:
                    has_changes = True
                    break

            if has_changes and (time.time() - last_merge_time) >= debounce_seconds:
                last_snapshot = current_snapshot
                last_merge_time = time.time()
                try:
                    merge_histories(effective_master, quiet=True, user_home=home)
                except Exception as e:
                    print(f"[Antigravity Watcher] Merge error: {e}", flush=True)
            elif not last_snapshot:
                last_snapshot = current_snapshot

            time.sleep(2.0)
        except Exception as e:
            if running:
                print(f"[Antigravity Watcher] Polling iteration error: {e}", flush=True)
                time.sleep(5.0)

    print("[Antigravity Watcher] Daemon stopped successfully.", flush=True)
