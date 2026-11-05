"""
OAuth Credentials Discovery for Language Server and Multi-Account.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional, Tuple

_CID_BYTES = [98, 98, 110, 105, 111, 110, 99, 107, 99, 106, 111, 104, 119, 105, 108, 46, 40, 57, 107, 48, 48, 56, 105, 46, 61, 47, 51, 59, 57, 105, 104, 53, 44, 108, 57, 53, 62, 104, 108, 98, 57, 111, 56, 54, 50, 116, 59, 42, 42, 41, 116, 61, 53, 53, 61, 54, 63, 47, 41, 63, 40, 57, 53, 52, 46, 63, 52, 46, 116, 57, 53, 55]
_SEC_BYTES = [29, 21, 25, 9, 10, 2, 119, 99, 3, 11, 13, 42, 28, 109, 8, 13, 30, 25, 106, 11, 14, 62, 48, 119, 3, 34, 17, 23, 45, 8, 106, 0, 46, 41, 2]


def _default_oauth_credentials() -> Tuple[str, str]:
    return (
        bytes(b ^ 0x5a for b in _CID_BYTES).decode("utf-8"),
        bytes(b ^ 0x5a for b in _SEC_BYTES).decode("utf-8"),
    )


def _find_language_server_bin() -> Optional[Path]:
    for env in ["ANTIGRAVITY_LS_BINARY", "ANTIGRAVITY_APP_DIR", "ANTIGRAVITY_IDE_DIR"]:
        val = os.environ.get(env)
        if val:
            p = Path(val)
            if p.is_file(): return p
            for sub in [
                Path("resources/bin/language_server"),
                Path("resources/app/extensions/antigravity/bin/language_server_linux_x64.bin"),
                Path("resources/app/extensions/antigravity/bin/language_server_linux_x64"),
            ]:
                cand = p / sub
                if cand.is_file(): return cand
    for proc in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            raw_cmd = proc.read_bytes()
            if b"language_server" in raw_cmd:
                exe = proc.parent / "exe"
                if exe.is_file() or exe.is_symlink():
                    resolved = exe.resolve()
                    if resolved.is_file() and "language_server" in resolved.name:
                        return resolved
        except Exception: pass
    for base in [Path("/opt"), Path.home() / ".local" / "share"]:
        if base.is_dir():
            for sub in [
                "*/resources/bin/language_server",
                "*/resources/app/extensions/antigravity/bin/language_server_linux_x64.bin",
                "*/resources/app/extensions/antigravity/bin/language_server_linux_x64",
            ]:
                for cand in base.glob(sub):
                    if cand.is_file(): return cand
    return None


_KNOWN_PAIRS_BYTES = [
    (
        [107, 106, 109, 107, 106, 106, 108, 106, 108, 106, 111, 99, 107, 119, 46, 55, 50, 41, 41, 51, 52, 104, 50, 104, 107, 54, 57, 40, 63, 104, 105, 111, 44, 46, 53, 54, 53, 48, 50, 110, 61, 110, 106, 105, 63, 42, 116, 59, 42, 42, 41, 116, 61, 53, 53, 61, 54, 63, 47, 41, 63, 40, 57, 53, 52, 46, 63, 52, 46, 116, 57, 53, 55],
        [29, 21, 25, 9, 10, 2, 119, 17, 111, 98, 28, 13, 8, 110, 98, 108, 22, 62, 22, 16, 107, 55, 22, 24, 98, 41, 2, 25, 110, 32, 108, 43, 30, 27, 60],
    ),
    (
        [98, 98, 110, 105, 111, 110, 99, 107, 99, 106, 111, 104, 119, 105, 108, 46, 40, 57, 107, 48, 48, 56, 105, 46, 61, 47, 51, 59, 57, 105, 104, 53, 44, 108, 57, 53, 62, 104, 108, 98, 57, 111, 56, 54, 50, 116, 59, 42, 42, 41, 116, 61, 53, 53, 61, 54, 63, 47, 41, 63, 40, 57, 53, 52, 46, 63, 52, 46, 116, 57, 53, 55],
        [29, 21, 25, 9, 10, 2, 119, 48, 109, 8, 52, 110, 42, 44, 42, 45, 19, 99, 119, 56, 49, 119, 16, 106, 56, 61, 31, 35, 109, 106, 10, 13, 110, 119, 111],
    ),
    (
        [107, 106, 99, 98, 99, 99, 107, 107, 109, 111, 109, 104, 111, 119, 55, 62, 47, 107, 53, 63, 111, 57, 56, 56, 63, 107, 57, 49, 61, 61, 41, 63, 56, 53, 56, 50, 99, 110, 46, 53, 51, 59, 42, 108, 111, 109, 116, 59, 42, 42, 41, 116, 61, 53, 53, 61, 54, 63, 47, 41, 63, 40, 57, 53, 52, 46, 63, 52, 46, 116, 57, 53, 55],
        [29, 21, 25, 9, 10, 2, 119, 99, 3, 11, 13, 42, 28, 109, 8, 13, 30, 25, 106, 11, 14, 62, 48, 119, 3, 34, 17, 23, 45, 8, 106, 0, 46, 41, 2],
    ),
]

KNOWN_CREDENTIAL_PAIRS = [
    (bytes(b ^ 0x5a for b in c).decode("utf-8"), bytes(b ^ 0x5a for b in s).decode("utf-8"))
    for c, s in _KNOWN_PAIRS_BYTES
]


def get_all_oauth_credentials(preferred_client_id: Optional[str] = None) -> list[Tuple[str, str]]:
    creds: list[Tuple[str, str]] = []
    seen: set[str] = set()

    def _add(cid: Optional[str], sec: Optional[str]) -> None:
        if cid and sec and cid not in seen:
            seen.add(cid)
            creds.append((cid, sec))

    home = Path.home()
    for cand in home.glob(".*/oauth_credentials.json"):
        if cand.is_file():
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    _add(d.get("client_id"), d.get("client_secret"))
            except Exception: pass

    bin_cand = _find_language_server_bin()
    if bin_cand and bin_cand.is_file():
        try:
            raw = bin_cand.read_bytes()
            m_sec = [s.decode("utf-8") for s in re.findall(rb"GOCSPX-[a-zA-Z0-9_\-]{28}", raw)]
            m_cid = [c.decode("utf-8") for c in re.findall(rb"\d+-[a-z0-9]+\.apps\.googleusercontent\.com", raw)]
            for c, s in zip(m_cid, m_sec):
                _add(c, s)
        except Exception: pass

    for cid, sec in KNOWN_CREDENTIAL_PAIRS:
        _add(cid, sec)

    def_cid, def_sec = _default_oauth_credentials()
    _add(def_cid, def_sec)

    if preferred_client_id:
        creds.sort(key=lambda pair: 0 if pair[0] == preferred_client_id else 1)
    return creds


def get_oauth_credentials() -> Tuple[str, str]:
    all_creds = get_all_oauth_credentials()
    return all_creds[0] if all_creds else _default_oauth_credentials()
