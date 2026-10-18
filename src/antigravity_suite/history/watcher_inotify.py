"""
Linux inotify Event Polling and Target Synchronization.
"""

from __future__ import annotations

import os
import struct
import time
from typing import List, Optional

from antigravity_suite.history.watcher_inotify_core import LinuxInotifyWatcherCore


class LinuxInotifyWatcher(LinuxInotifyWatcherCore):
    """Zero-CPU kernel-level file monitoring using Linux inotify and epoll."""

    def sync_watch_targets(self, conv_dirs: List[str], brain_dirs: List[str], extra_dirs: Optional[List[str]] = None) -> None:
        if not self.available:
            return
        for cd in conv_dirs:
            self.add_watch_dir(cd)
        for bd in brain_dirs:
            if os.path.isdir(bd):
                self.add_watch_dir(bd)
                try:
                    for entry in os.scandir(bd):
                        if entry.is_dir():
                            self.add_watch_dir(entry.path)
                            logs_d = os.path.join(entry.path, ".system_generated", "logs")
                            if os.path.isdir(logs_d):
                                self.add_watch_dir(logs_d)
                except Exception:
                    pass
        for ed in (extra_dirs or []):
            if os.path.isdir(ed):
                self.add_watch_dir(ed)

    def wait_for_events(self, timeout_sec: float = 2.0) -> List[str]:
        if not self.available or self._epoll is None:
            time.sleep(timeout_sec)
            return []
        changed = []
        try:
            if not self._epoll.poll(timeout=timeout_sec):
                return []
            while True:
                try:
                    data = os.read(self._fd, 8192)
                    if not data:
                        break
                    offset = 0
                    while offset + 16 <= len(data):
                        wd, _, _, name_len = struct.unpack_from("iIII", data, offset)
                        offset += 16
                        name = data[offset : offset + name_len].split(b"\x00", 1)[0].decode("utf-8", errors="ignore") if name_len > 0 else ""
                        offset += name_len
                        base_dir = self._wd_to_path.get(wd)
                        if base_dir:
                            changed.append(os.path.join(base_dir, name) if name else base_dir)
                except (BlockingIOError, OSError):
                    break
        except Exception:
            pass
        return changed

    def drain_events(self) -> None:
        if self.available and self._fd >= 0:
            try:
                while os.read(self._fd, 65536):
                    pass
            except (BlockingIOError, OSError):
                pass
