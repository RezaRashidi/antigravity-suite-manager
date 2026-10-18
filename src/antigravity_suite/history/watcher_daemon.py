"""
Real-Time Watcher Daemon Main Loop Execution.
"""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path
from typing import Optional, Union

from antigravity_suite.config import get_user_home
from antigravity_suite.history.merger import merge_histories
from antigravity_suite.history.watcher_debounce import DebounceTracker, is_relevant_event
from antigravity_suite.history.watcher_inotify import LinuxInotifyWatcher
from antigravity_suite.history.watcher_targets import discover_watch_targets, get_mtime_snapshot


def watch_mode(
    master_gemini: Optional[Union[str, Path]] = None,
    user_home: Optional[Union[str, Path]] = None,
    debounce_seconds: float = 3.0,
) -> None:
    """Monitors conversation directories and executes incremental merges on modification."""
    home = Path(user_home).resolve() if user_home else get_user_home()
    master = Path(master_gemini).resolve() if master_gemini else (home / ".gemini" / "antigravity")
    running = True

    def _sig(signum: int, frame: object) -> None:
        nonlocal running
        print(f"\n[Antigravity Watcher] Received signal {signum}, stopping...", flush=True)
        running = False

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    print("[Antigravity Watcher] Initializing real-time history synchronization daemon...", flush=True)

    try:
        merge_histories(master, quiet=True, user_home=home)
    except Exception as e:
        print(f"[Antigravity Watcher] Warning: Initial merge error: {e}", flush=True)

    conv_dirs, brain_dirs, extra_dirs, extra_files = discover_watch_targets(master, home)
    last_snap = get_mtime_snapshot(conv_dirs, brain_dirs, extra_files)
    inotify = LinuxInotifyWatcher()
    if inotify.available:
        inotify.sync_watch_targets(conv_dirs, brain_dirs, extra_dirs)

    tracker, last_disc = DebounceTracker(debounce_seconds), time.time()

    while running:
        try:
            now = time.time()
            if (now - last_disc) >= 60.0:
                conv_dirs, brain_dirs, extra_dirs, extra_files = discover_watch_targets(master, home)
                last_disc = now
                if inotify.available:
                    inotify.sync_watch_targets(conv_dirs, brain_dirs, extra_dirs)

            if inotify.available:
                for ev in inotify.wait_for_events(timeout_sec=2.0):
                    if os.path.isdir(ev):
                        inotify.add_watch_dir(ev)
                    if is_relevant_event(ev):
                        tracker.record_change(ev, now)
                        break
            else:
                cur_snap = get_mtime_snapshot(conv_dirs, brain_dirs)
                for f, mt in cur_snap.items():
                    if f not in last_snap or last_snap[f] < mt:
                        tracker.record_change(f, now)
                        break
                last_snap, _ = cur_snap, time.sleep(2.0)

            should_trig, reason = tracker.should_trigger(time.time())
            if should_trig:
                print(f"[Antigravity Watcher] Sync triggered: {reason} on {tracker.pending_file}...", flush=True)
                try:
                    merge_histories(master, quiet=True, user_home=home, skip_backup=True)
                except Exception as e:
                    print(f"[Antigravity Watcher] Merge error: {e}", flush=True)
                if inotify.available:
                    inotify.drain_events()
                    inotify.sync_watch_targets(conv_dirs, brain_dirs)
                else:
                    last_snap = get_mtime_snapshot(conv_dirs, brain_dirs)
                tracker.reset()
        except Exception as e:
            if running:
                time.sleep(5.0)

    if inotify.available:
        inotify.close()
    print("[Antigravity Watcher] Daemon stopped successfully.", flush=True)
