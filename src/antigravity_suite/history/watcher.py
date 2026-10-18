"""
Real-Time File Watcher and Synchronization Daemon Facade.
"""

from __future__ import annotations

from antigravity_suite.history.watcher_daemon import watch_mode
from antigravity_suite.history.watcher_inotify import LinuxInotifyWatcher

__all__ = ["LinuxInotifyWatcher", "watch_mode"]
