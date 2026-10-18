"""
Google OAuth Token Refresh Execution and Atomic Persistence.
"""

from __future__ import annotations

import datetime
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Union

from antigravity_suite.auth.credentials import check_token_needs_refresh, load_oauth_credentials
from antigravity_suite.config import get_user_home


def refresh_ide_oauth_token(
    ide_dir: Optional[Union[str, Path]] = None,
    user_home: Optional[Union[str, Path]] = None,
) -> bool:
    """Refreshes expired or near-expired OAuth token for Antigravity IDE."""
    home = str(user_home) if user_home else str(get_user_home())
    effective_ide = str(ide_dir) if ide_dir else os.path.join(home, ".gemide")
    token_file = os.path.join(effective_ide, "jetski-standalone-oauth-token")
    oauth_file = os.path.join(effective_ide, "oauth_credentials.json")

    if not os.path.isfile(token_file) and ide_dir is None:
        effective_ide = os.path.join(home, ".gemini")
        token_file = os.path.join(effective_ide, "jetski-standalone-oauth-token")
        oauth_file = os.path.join(effective_ide, "oauth_credentials.json")

    if not os.path.isfile(token_file):
        return False

    try:
        with open(token_file, "r", encoding="utf-8") as f:
            token_data = json.load(f)
    except Exception:
        return False

    needs_refresh, refresh_token = check_token_needs_refresh(token_data)
    if not needs_refresh or not refresh_token:
        return False

    client_id, client_secret = load_oauth_credentials(oauth_file, home)
    if not client_id or not client_secret:
        return False

    return _execute_refresh_request(token_file, token_data, client_id, client_secret, refresh_token)


def _execute_refresh_request(token_file: str, token_data: dict, cid: str, csec: str, rtoken: str) -> bool:
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": cid,
        "client_secret": csec,
        "refresh_token": rtoken,
        "grant_type": "refresh_token",
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(token_url, data=data, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            new_access_token = resp_data.get("access_token")
            expires_in = resp_data.get("expires_in", 3600)
            if new_access_token:
                inner = token_data.setdefault("token", {})
                inner["access_token"] = new_access_token
                new_expiry = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in)).strftime(
                    "%Y-%m-%dT%H:%M:%S.000000+00:00"
                )
                inner["expiry"] = new_expiry

                tmp_file = token_file + ".tmp"
                fd = os.open(tmp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(token_data, f, indent=2)
                os.replace(tmp_file, token_file)
                return True
    except Exception:
        pass
    return False
