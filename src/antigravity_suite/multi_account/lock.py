"""PID lockfile utilities for multi-account CLI and daemons."""

from __future__ import annotations

import os
import signal
import time
from antigravity_suite.multi_account.vault import get_accounts_dir


def acquire_pid_lock(name: str = "login.pid") -> bool:
    lock_file = get_accounts_dir() / name
    if lock_file.exists():
        try:
            old_pid = int(lock_file.read_text().strip())
            if old_pid != os.getpid():
                try:
                    os.kill(old_pid, signal.SIGTERM)
                    time.sleep(0.15)
                except OSError:
                    pass
        except Exception:
            pass
    try:
        lock_file.write_text(str(os.getpid()))
        return True
    except Exception:
        return False


def release_pid_lock(name: str = "login.pid") -> None:
    try:
        lock_file = get_accounts_dir() / name
        if lock_file.exists():
            lock_file.unlink(missing_ok=True)
    except Exception:
        pass
