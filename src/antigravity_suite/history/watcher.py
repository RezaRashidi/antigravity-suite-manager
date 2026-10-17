"""
Real-Time File Watcher and Synchronization Daemon for Antigravity History.

Monitors conversation directories across all instances using inotify or
timestamp polling with intelligent event debouncing and clean POSIX signal termination.
"""

from __future__ import annotations

import ctypes
import glob
import os
import select
import signal
import struct
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from antigravity_suite.config import DEFAULT_CONFIG, get_user_home
from antigravity_suite.history.discovery import discover_all_history_sources
from antigravity_suite.history.merger import merge_histories


class LinuxInotifyWatcher:
    """Zero-CPU kernel-level file monitoring using Linux inotify and epoll."""

    IN_MODIFY = 0x00000002
    IN_CLOSE_WRITE = 0x00000008
    IN_MOVED_TO = 0x00000080
    IN_CREATE = 0x00000100
    IN_DELETE = 0x00000200

    def __init__(self) -> None:
        self.available = False
        self._libc: Optional[ctypes.CDLL] = None
        self._fd = -1
        self._epoll: Optional[select.epoll] = None
        self._wd_to_path: Dict[int, str] = {}
        self._path_to_wd: Dict[str, int] = {}

        if sys.platform != "linux":
            return

        try:
            self._libc = ctypes.CDLL("libc.so.6", use_errno=True)
            if not hasattr(self._libc, "inotify_init1") or not hasattr(self._libc, "inotify_add_watch"):
                return
            self._libc.inotify_init1.argtypes = [ctypes.c_int]
            self._libc.inotify_init1.restype = ctypes.c_int
            self._libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
            self._libc.inotify_add_watch.restype = ctypes.c_int
            self._libc.inotify_rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
            self._libc.inotify_rm_watch.restype = ctypes.c_int

            # IN_NONBLOCK = 0x00000800, IN_CLOEXEC = 0x00080000
            self._fd = self._libc.inotify_init1(0x00080800)
            if self._fd < 0:
                self._fd = self._libc.inotify_init()
            if self._fd < 0:
                return

            self._epoll = select.epoll()
            self._epoll.register(self._fd, select.EPOLLIN)
            self.available = True
        except Exception:
            self.available = False

    def add_watch_dir(self, dir_path: str) -> bool:
        if not self.available or self._libc is None or not os.path.isdir(dir_path):
            return False
        real_p = os.path.realpath(dir_path)
        if real_p in self._path_to_wd:
            return True
        try:
            mask = (
                self.IN_MODIFY
                | self.IN_CLOSE_WRITE
                | self.IN_MOVED_TO
                | self.IN_CREATE
                | self.IN_DELETE
            )
            wd = self._libc.inotify_add_watch(self._fd, real_p.encode("utf-8"), mask)
            if wd >= 0:
                self._wd_to_path[wd] = real_p
                self._path_to_wd[real_p] = wd
                return True
        except Exception:
            pass
        return False

    def sync_watch_targets(self, conv_dirs: List[str], brain_dirs: List[str]) -> None:
        """Adds watches for conv directories, brain root directories, and active log directories."""
        if not self.available:
            return
        for cd in conv_dirs:
            self.add_watch_dir(cd)
        for bd in brain_dirs:
            if not os.path.isdir(bd):
                continue
            self.add_watch_dir(bd)
            try:
                for entry in os.scandir(bd):
                    if entry.is_dir():
                        logs_d = os.path.join(entry.path, ".system_generated", "logs")
                        if os.path.isdir(logs_d):
                            self.add_watch_dir(logs_d)
            except Exception:
                pass

    def wait_for_events(self, timeout_sec: float = 2.0) -> List[str]:
        """Waits using epoll on the inotify file descriptor. Zero CPU when idle."""
        if not self.available or self._epoll is None:
            time.sleep(timeout_sec)
            return []

        changed_paths = []
        try:
            events = self._epoll.poll(timeout=timeout_sec)
            if not events:
                return []

            while True:
                try:
                    data = os.read(self._fd, 8192)
                    if not data:
                        break
                    offset = 0
                    while offset + 16 <= len(data):
                        wd, mask, cookie, name_len = struct.unpack_from("iIII", data, offset)
                        offset += 16
                        name = ""
                        if name_len > 0:
                            raw_name = data[offset : offset + name_len].split(b"\x00", 1)[0]
                            name = raw_name.decode("utf-8", errors="ignore")
                            offset += name_len
                        base_dir = self._wd_to_path.get(wd)
                        if base_dir:
                            full_path = os.path.join(base_dir, name) if name else base_dir
                            changed_paths.append(full_path)
                except BlockingIOError:
                    break
                except Exception:
                    break
        except Exception:
            pass

        return changed_paths

    def close(self) -> None:
        if self._epoll:
            try:
                self._epoll.close()
            except Exception:
                pass
        if self._fd >= 0:
            try:
                os.close(self._fd)
            except Exception:
                pass


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
        else Path(
            os.environ.get(
                "ANTIGRAVITY_DATA_DIR",
                os.environ.get("ANTIGRAVITY_HISTORY_DIR", home / ".gemini" / "antigravity")
            )
        ).resolve()
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

    def _get_mtime_snapshot(conv_dirs: List[str], brain_dirs: List[str]) -> Dict[str, float]:
        snapshot: Dict[str, float] = {}
        for d in conv_dirs:
            if not os.path.isdir(d):
                continue
            for f in glob.glob(os.path.join(d, "*.db")):
                basename = os.path.basename(f)
                if basename.startswith("conversation_summaries"):
                    continue
                try:
                    snapshot[f] = os.path.getmtime(f)
                except Exception:
                    pass
        for b in brain_dirs:
            if not os.path.isdir(b):
                continue
            for pattern in [
                os.path.join(b, "*", ".system_generated", "logs", "*.jsonl"),
                os.path.join(b, "*", "*.md"),
            ]:
                for f in glob.glob(pattern):
                    try:
                        snapshot[f] = os.path.getmtime(f)
                    except Exception:
                        pass
        return snapshot

    conv_pools, brain_pools, _ = discover_all_history_sources(user_home=home)
    watch_conv_dirs = list(set([str(effective_master / "conversations")] + conv_pools))
    watch_brain_dirs = list(set([str(effective_master / "brain")] + brain_pools))
    last_snapshot = _get_mtime_snapshot(watch_conv_dirs, watch_brain_dirs)
    last_merge_time = time.time()

    inotify = LinuxInotifyWatcher()
    if inotify.available:
        inotify.sync_watch_targets(watch_conv_dirs, watch_brain_dirs)
        print(f"[Antigravity Watcher] Linux inotify kernel monitoring enabled (0% idle CPU).", flush=True)

    print(f"[Antigravity Watcher] Actively monitoring conversation directories for modifications...", flush=True)

    last_discovery_time = time.time()
    first_change_time: Optional[float] = None
    last_change_time: Optional[float] = None
    burst_count = 0
    pending_file: Optional[str] = None

    while running:
        try:
            now = time.time()
            if (now - last_discovery_time) >= 60.0:
                conv_pools, brain_pools, _ = discover_all_history_sources(user_home=home)
                watch_conv_dirs = list(set([str(effective_master / "conversations")] + conv_pools))
                watch_brain_dirs = list(set([str(effective_master / "brain")] + brain_pools))
                last_discovery_time = now
                if inotify.available:
                    inotify.sync_watch_targets(watch_conv_dirs, watch_brain_dirs)

            has_changes = False
            changed_file = None

            if inotify.available:
                # Kernel-level event waiting (blocks in epoll with 0 CPU usage during timeout)
                events = inotify.wait_for_events(timeout_sec=2.0)
                for ev_path in events:
                    base = os.path.basename(ev_path)
                    if not base or base.startswith("conversation_summaries"):
                        continue
                    if (
                        base.endswith(".db")
                        or base.endswith(".jsonl")
                        or base.endswith(".pbtxt")
                        or base.endswith(".md")
                    ):
                        has_changes = True
                        changed_file = (ev_path, None, time.time())
                        break
            else:
                # Fallback to mtime snapshot polling on non-Linux or fallback mode
                current_snapshot = _get_mtime_snapshot(watch_conv_dirs, watch_brain_dirs)
                for f, mtime in current_snapshot.items():
                    if f not in last_snapshot or last_snapshot[f] < mtime:
                        has_changes = True
                        changed_file = (f, last_snapshot.get(f), mtime)
                        break
                time.sleep(2.0)

            if has_changes:
                if first_change_time is None:
                    first_change_time = now
                    burst_count = 1
                else:
                    burst_count += 1
                last_change_time = now
                pending_file = changed_file[0]
                if not inotify.available:
                    last_snapshot = current_snapshot

            should_trigger = False
            trigger_reason = ""
            if first_change_time is not None and last_change_time is not None:
                quiet_duration = now - last_change_time
                total_duration = now - first_change_time
                required_quiet = debounce_seconds if burst_count <= 1 else min(debounce_seconds * 2.5, 8.0)

                if quiet_duration >= required_quiet:
                    should_trigger = True
                    trigger_reason = f"quiet period settled ({quiet_duration:.1f}s >= {required_quiet:.1f}s, bursts={burst_count})"
                elif total_duration >= 15.0:
                    should_trigger = True
                    trigger_reason = f"hard deadline ceiling reached ({total_duration:.1f}s >= 15.0s, bursts={burst_count})"

            if should_trigger:
                print(
                    f"[Antigravity Watcher] Sync triggered: {trigger_reason} on {pending_file}...",
                    flush=True,
                )
                try:
                    merge_histories(effective_master, quiet=True, user_home=home, skip_backup=True)
                except Exception as e:
                    print(f"[Antigravity Watcher] Merge error: {e}", flush=True)

                if inotify.available:
                    inotify.sync_watch_targets(watch_conv_dirs, watch_brain_dirs)
                else:
                    last_snapshot = _get_mtime_snapshot(watch_conv_dirs, watch_brain_dirs)

                last_merge_time = time.time()
                first_change_time = None
                last_change_time = None
                burst_count = 0
                pending_file = None
            elif not inotify.available and not last_snapshot:
                last_snapshot = current_snapshot
        except Exception as e:
            if running:
                print(f"[Antigravity Watcher] Polling iteration error: {e}", flush=True)
                time.sleep(5.0)

    if inotify.available:
        inotify.close()

    print("[Antigravity Watcher] Daemon stopped successfully.", flush=True)
