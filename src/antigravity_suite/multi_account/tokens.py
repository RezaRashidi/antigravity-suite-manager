"""OAuth Token management and refreshing for multi-account vault."""

from __future__ import annotations

import base64
import datetime
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Tuple


_CID_BYTES = [107, 106, 109, 107, 106, 106, 108, 106, 108, 106, 111, 99, 107, 119, 46, 55, 50, 41, 41, 51, 52, 104, 50, 104, 107, 54, 57, 40, 63, 104, 105, 111, 44, 46, 53, 54, 53, 48, 50, 110, 61, 110, 106, 105, 63, 42, 116, 59, 42, 42, 41, 116, 61, 53, 53, 61, 54, 63, 47, 41, 63, 40, 57, 53, 52, 46, 63, 52, 46, 116, 57, 53, 55]
_SEC_BYTES = [29, 21, 25, 9, 10, 2, 119, 17, 111, 98, 28, 13, 8, 110, 98, 108, 22, 62, 22, 16, 107, 55, 22, 24, 98, 41, 2, 25, 110, 32, 108, 43, 30, 27, 60]


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


def get_oauth_credentials() -> Tuple[str, str]:
    home = Path.home()
    for cand in home.glob(".*/oauth_credentials.json"):
        if cand.is_file():
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if d.get("client_id") and d.get("client_secret"):
                        return d["client_id"], d["client_secret"]
            except Exception: pass
    bin_cand = _find_language_server_bin()
    if bin_cand and bin_cand.is_file():
        try:
            raw = bin_cand.read_bytes()
            m_sec = [s.decode("utf-8") for s in re.findall(rb"GOCSPX-[a-zA-Z0-9_\-]{28}", raw)]
            m_cid = [c.decode("utf-8") for c in re.findall(rb"\d+-[a-z0-9]+\.apps\.googleusercontent\.com", raw)]
            for c, s in zip(m_cid, m_sec):
                if "1071006060591" in c: return c, s
            for c, s in zip(m_cid, m_sec):
                if "884354919052" not in c: return c, s
        except Exception: pass
    return _default_oauth_credentials()


def parse_jwt_claims(id_token: str) -> dict:
    try:
        parts = id_token.split(".")
        if len(parts) >= 2:
            payload = parts[1] + "=" * (-len(parts[1]) % 4)
            return json.loads(base64.b64decode(payload).decode("utf-8"))
    except Exception: pass
    return {}


def is_token_expired(expiry_str: str, buffer_seconds: int = 300) -> bool:
    if not expiry_str: return True
    try:
        clean = re.sub(r"(\.\d{6})\d+", r"\1", expiry_str.replace("Z", "+00:00"))
        exp_dt = datetime.datetime.fromisoformat(clean)
        if exp_dt.tzinfo is None: exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)
        return (exp_dt - datetime.datetime.now(datetime.timezone.utc)).total_seconds() < buffer_seconds
    except Exception: return True


def refresh_access_token(
    refresh_token: str, client_id: Optional[str] = None, client_secret: Optional[str] = None
) -> Optional[Tuple[str, str, int]]:
    if not refresh_token: return None
    cid, sec = (client_id, client_secret) if (client_id and client_secret) else get_oauth_credentials()
    if not cid or not sec: return None
    payload = {"client_id": cid, "client_secret": sec, "refresh_token": refresh_token, "grant_type": "refresh_token"}
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=urllib.parse.urlencode(payload).encode("utf-8"), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            new_acc, exp_in = data.get("access_token"), data.get("expires_in", 3600)
            if new_acc:
                new_exp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=exp_in)).strftime("%Y-%m-%dT%H:%M:%S.000000+00:00")
                return new_acc, new_exp, exp_in
    except Exception: pass
    return None
