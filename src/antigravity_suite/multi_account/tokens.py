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


def _find_language_server_bin() -> Optional[Path]:
    for env in ["ANTIGRAVITY_LS_BINARY", "ANTIGRAVITY_APP_DIR"]:
        val = os.environ.get(env)
        if val:
            p = Path(val)
            if p.is_file(): return p
            cand = p / "resources" / "bin" / "language_server"
            if cand.is_file(): return cand
    for proc in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            if b"language_server" in proc.read_bytes():
                exe = proc.parent / "exe"
                if exe.is_file() or exe.is_symlink(): return exe.resolve()
        except Exception: pass
    for cand in Path("/opt").glob("*/resources/bin/language_server"):
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
            m_sec = re.search(rb"GOCSPX-[a-zA-Z0-9_\-]+", raw)
            m_cid = re.search(rb"\d+-[a-z0-9]+\.apps\.googleusercontent\.com", raw)
            if m_sec and m_cid: return m_cid.group(0).decode("utf-8"), m_sec.group(0).decode("utf-8")
        except Exception: pass
    return "", ""


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
