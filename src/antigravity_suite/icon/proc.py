"""
Process telemetry and boot timing for icon process association.
"""

from __future__ import annotations

import os
from typing import Optional


def get_boot_time() -> int:
    """Reads system btime from /proc/stat."""
    try:
        with open("/proc/stat", "r") as f:
            for line in f:
                if line.startswith("btime "):
                    return int(line.split()[1])
    except Exception:
        pass
    return 0


_BOOT_TIME = get_boot_time()
_CLK_TCK = os.sysconf(os.sysconf_names.get('SC_CLK_TCK', 'SC_CLK_TCK')) if hasattr(os, 'sysconf') else 100


def get_proc_start_time(pid: int) -> Optional[int]:
    """Reads starttime field of pid from /proc/<pid>/stat."""
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            data = f.read()
            comm_end = data.rfind(')')
            if comm_end != -1:
                fields = data[comm_end + 2:].split()
                return int(fields[19])
    except Exception:
        pass
    return None
