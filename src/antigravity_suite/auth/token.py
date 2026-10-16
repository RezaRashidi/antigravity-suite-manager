"""
Google OAuth2 Credential Management and Token Refresh for Antigravity.

Handles automated OAuth token renewal for jetski-standalone-oauth-token
without triggering UI logout or requiring browser re-authentication.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Union

from antigravity_suite.config import get_user_home


def refresh_ide_oauth_token(
    ide_dir: Optional[Union[str, Path]] = None,
    user_home: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Checks `jetski-standalone-oauth-token` in `ide_dir` (default: ~/.gemide).
    If expired or within 5 minutes of expiration, refreshes the access token using Google OAuth.
    Returns True if refreshed, False otherwise.
    """
    home = str(user_home) if user_home else str(get_user_home())
    effective_ide = str(ide_dir) if ide_dir else os.path.join(home, ".gemide")
    token_file = os.path.join(effective_ide, "jetski-standalone-oauth-token")
    oauth_file = os.path.join(effective_ide, "oauth_credentials.json")

    # Fallback to ~/.gemini only if ide_dir was not explicitly passed
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

    inner_token = token_data.get("token", {})
    refresh_token = inner_token.get("refresh_token")
    expiry_str = inner_token.get("expiry")

    if not refresh_token:
        return False

    # Check expiration (treat within 300 seconds as expired)
    needs_refresh = False
    if expiry_str:
        try:
            exp_clean = expiry_str.replace("Z", "+00:00")
            exp_clean = re.sub(r"(\.\d{6})\d+", r"\1", exp_clean)
            exp_dt = datetime.datetime.fromisoformat(exp_clean)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            if (exp_dt - now_dt).total_seconds() < 300:
                needs_refresh = True
        except Exception:
            needs_refresh = True
    else:
        needs_refresh = True

    if not needs_refresh:
        return False

    # Client credentials
    client_id = None
    client_secret = None
    if os.path.isfile(oauth_file):
        try:
            with open(oauth_file, "r", encoding="utf-8") as f:
                c_data = json.load(f)
                client_id = c_data.get("client_id")
                client_secret = c_data.get("client_secret")
        except Exception:
            pass

    if not client_id or not client_secret:
        # Fallback to primary ~/.gemini/oauth_credentials.json
        primary_oauth = os.path.join(home, ".gemini", "oauth_credentials.json")
        if os.path.isfile(primary_oauth):
            try:
                with open(primary_oauth, "r", encoding="utf-8") as f:
                    c_data = json.load(f)
                    client_id = client_id or c_data.get("client_id")
                    client_secret = client_secret or c_data.get("client_secret")
            except Exception:
                pass

    if not client_id or not client_secret:
        return False

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
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
                inner_token["access_token"] = new_access_token
                new_expiry = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in)).strftime(
                    "%Y-%m-%dT%H:%M:%S.000000+00:00"
                )
                inner_token["expiry"] = new_expiry
                token_data["token"] = inner_token

                # Write back atomically with restricted 0o600 permissions
                tmp_file = token_file + ".tmp"
                fd = os.open(tmp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(token_data, f, indent=2)
                os.replace(tmp_file, token_file)
                return True
    except Exception:
        pass

    return False
