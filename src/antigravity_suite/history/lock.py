"""
Process Singleton File Locking for History Merging and Daemon Monitoring.
"""

from __future__ import annotations

import fcntl
import os
import time
from typing import Optional


class ProcessLock:
    """Acquires and releases exclusive OS file locks to enforce singleton processes."""

    def __init__(self, name: str = "antigravity_merge_history") -> None:
        self.lock_path = f"/tmp/{name}.lock"
        self._fd: Optional[int] = None

    def acquire(self, non_blocking: bool = True, timeout_sec: float = 0.0) -> bool:
        start_time = time.time()
        while True:
            try:
                self._fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o666)
                flags = fcntl.LOCK_EX
                if non_blocking and timeout_sec <= 0.0:
                    flags |= fcntl.LOCK_NB
                fcntl.flock(self._fd, flags)
                os.ftruncate(self._fd, 0)
                os.write(self._fd, f"{os.getpid()}\n".encode("utf-8"))
                return True
            except (BlockingIOError, OSError):
                if self._fd is not None:
                    try:
                        os.close(self._fd)
                    except Exception:
                        pass
                    self._fd = None
                if non_blocking:
                    if timeout_sec > 0.0 and (time.time() - start_time) < timeout_sec:
                        time.sleep(0.1)
                        continue
                    return False
                time.sleep(0.1)

    def release(self) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
