"""
OAuth Client Credentials and Token Expiration Check.
"""

from __future__ import annotations

import datetime
import json
import os
import re
from typing import Optional, Tuple


def check_token_needs_refresh(token_data: dict) -> Tuple[bool, Optional[str]]:
    """Checks whether the token is missing, expired, or within 300s of expiry."""
    inner_token = token_data.get("token", {})
    refresh_token = inner_token.get("refresh_token")
    expiry_str = inner_token.get("expiry")

    if not refresh_token:
        return False, None

    if not expiry_str:
        return True, refresh_token

    try:
        exp_clean = expiry_str.replace("Z", "+00:00")
        exp_clean = re.sub(r"(\.\d{6})\d+", r"\1", exp_clean)
        exp_dt = datetime.datetime.fromisoformat(exp_clean)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        if (exp_dt - now_dt).total_seconds() < 300:
            return True, refresh_token
    except Exception:
        return True, refresh_token

    return False, refresh_token


def load_oauth_credentials(oauth_file: str, home: str) -> Tuple[Optional[str], Optional[str]]:
    """Loads client_id and client_secret from file or fallback home location."""
    for path in [oauth_file, os.path.join(home, ".gemini", "oauth_credentials.json")]:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    c_data = json.load(f)
                    cid = c_data.get("client_id")
                    sec = c_data.get("client_secret")
                    if cid and sec:
                        return cid, sec
            except Exception:
                pass
    return None, None
