"""
Linux inotify FFI Bindings and Core File Descriptor Management.
"""

from __future__ import annotations

import ctypes
import os
import select
import sys
from typing import Dict, Optional


class LinuxInotifyWatcherCore:
    """Core Linux inotify FFI bindings and watch descriptor registry."""

    IN_MODIFY = 0x00000002
    IN_CLOSE_WRITE = 0x00000008
    IN_MOVED_TO = 0x00000080
    IN_CREATE = 0x00000100
    IN_DELETE = 0x00000200

    def __init__(self) -> None:
        self.available, self._libc, self._fd, self._epoll = False, None, -1, None
        self._wd_to_path: Dict[int, str] = {}
        self._path_to_wd: Dict[str, int] = {}
        if sys.platform != "linux":
            return
        try:
            self._libc = ctypes.CDLL("libc.so.6", use_errno=True)
            self._libc.inotify_init1.argtypes = [ctypes.c_int]
            self._libc.inotify_init1.restype = ctypes.c_int
            self._libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
            self._libc.inotify_add_watch.restype = ctypes.c_int
            self._libc.inotify_rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
            self._libc.inotify_rm_watch.restype = ctypes.c_int

            self._fd = self._libc.inotify_init1(0x00080800)
            if self._fd < 0:
                self._fd = self._libc.inotify_init()
            if self._fd >= 0:
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
            mask = self.IN_MODIFY | self.IN_CLOSE_WRITE | self.IN_MOVED_TO | self.IN_CREATE | self.IN_DELETE
            wd = self._libc.inotify_add_watch(self._fd, real_p.encode("utf-8"), mask)
            if wd >= 0:
                self._wd_to_path[wd] = real_p
                self._path_to_wd[real_p] = wd
                return True
        except Exception:
            pass
        return False

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
