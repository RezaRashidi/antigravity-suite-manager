"""
Authentic Installed User-Agent Resolution for Antigravity Google Cloud Code RPCs.
"""

from __future__ import annotations

import json
import os
import platform
import struct
import sys
import time
from typing import Optional

_CACHED_UA: Optional[str] = None
_CACHED_VERSION: Optional[str] = None
_LAST_CHECK: float = 0.0


def get_installed_version() -> str:
    global _CACHED_VERSION, _LAST_CHECK
    now = time.time()
    if _CACHED_VERSION and (now - _LAST_CHECK < 60.0):
        return _CACHED_VERSION

    # 1. Try reading /proc for running language_server
    try:
        if os.path.isdir("/proc"):
            for pid in os.listdir("/proc"):
                if pid.isdigit():
                    try:
                        with open(f"/proc/{pid}/cmdline", "rb") as f:
                            cmd = f.read().decode("utf-8", errors="ignore")
                        if "language_server" in cmd and "--override_ide_version" in cmd:
                            parts = cmd.split("\0")
                            for i, p in enumerate(parts):
                                if p == "--override_ide_version" and i + 1 < len(parts):
                                    v = parts[i + 1].strip()
                                    if v:
                                        _CACHED_VERSION = v
                                        _LAST_CHECK = now
                                        return _CACHED_VERSION
                    except Exception:
                        pass
    except Exception:
        pass

    # 2. Try reading package.json from common installation paths
    cands = [
        "/opt/antigravity2/resources/app/package.json",
        "/opt/antigravity/resources/app/package.json",
    ]
    for p in cands:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    pkg = json.load(f)
                if pkg.get("version"):
                    _CACHED_VERSION = str(pkg["version"]).strip()
                    _LAST_CHECK = now
                    return _CACHED_VERSION
            except Exception:
                pass

    # 3. Try reading directly from asar header
    asar_cands = [
        "/opt/antigravity2/resources/app.asar",
        "/opt/antigravity/resources/app.asar",
    ]
    for asar_path in asar_cands:
        if os.path.isfile(asar_path):
            try:
                with open(asar_path, "rb") as f:
                    f.seek(4)
                    total_header_size = struct.unpack("<I", f.read(4))[0]
                    f.seek(12)
                    json_len = struct.unpack("<I", f.read(4))[0]
                    header = json.loads(f.read(json_len).decode("utf-8"))
                    pkg_entry = header.get("files", {}).get("package.json", {})
                    if pkg_entry:
                        offset = int(pkg_entry.get("offset", 0))
                        size = int(pkg_entry.get("size", 0))
                        payload_start = 8 + total_header_size
                        f.seek(payload_start + offset)
                        pkg = json.loads(f.read(size).decode("utf-8"))
                        if pkg.get("version"):
                            _CACHED_VERSION = str(pkg["version"]).strip()
                            _LAST_CHECK = now
                            return _CACHED_VERSION
            except Exception:
                pass

    _CACHED_VERSION = "2.29.1"
    _LAST_CHECK = now
    return _CACHED_VERSION


def get_authentic_user_agent() -> str:
    global _CACHED_UA, _LAST_CHECK
    now = time.time()
    if _CACHED_UA and (now - _LAST_CHECK < 60.0):
        return _CACHED_UA

    os_map = {"linux": "linux", "darwin": "darwin", "win32": "windows"}
    os_type = os_map.get(sys.platform, sys.platform)

    machine = platform.machine().lower()
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "i386": "386",
        "i686": "386",
    }
    arch = arch_map.get(machine, machine)
    ver = get_installed_version()

    _CACHED_UA = f"antigravity/hub/{ver} (os_type={os_type}; arch={arch})"
    return _CACHED_UA
