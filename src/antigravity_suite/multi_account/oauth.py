"""OAuth loopback server for authenticating new Google accounts."""

from __future__ import annotations

import http.server
import urllib.parse
import webbrowser
from typing import Optional

from antigravity_suite.multi_account.lock import acquire_pid_lock, release_pid_lock
from antigravity_suite.multi_account.models import AccountRecord
from antigravity_suite.multi_account.oauth_exchange import exchange_auth_code
from antigravity_suite.multi_account.oauth_handler import OAuthHandler
from antigravity_suite.multi_account.tokens import get_oauth_credentials

acquire_login_lock = acquire_pid_lock
release_login_lock = release_pid_lock

__all__ = [
    "acquire_login_lock",
    "exchange_auth_code",
    "release_login_lock",
    "start_login_flow",
]


def start_login_flow(open_browser: bool = True, timeout: int = 180) -> Optional[AccountRecord]:
    acquire_login_lock()
    srv = http.server.HTTPServer(("127.0.0.1", 0), OAuthHandler)
    srv.timeout = timeout
    srv.auth_code = None  # type: ignore
    srv.account_record = None  # type: ignore
    try:
        port = srv.server_port
        redirect_uri = f"http://127.0.0.1:{port}/callback"
        cid, _ = get_oauth_credentials()
        scopes = (
            "openid profile email "
            "https://www.googleapis.com/auth/cloud-platform "
            "https://www.googleapis.com/auth/userinfo.email "
            "https://www.googleapis.com/auth/userinfo.profile "
            "https://www.googleapis.com/auth/cclog "
            "https://www.googleapis.com/auth/experimentsandconfigs"
        )
        params = {
            "client_id": cid, "redirect_uri": redirect_uri, "response_type": "code",
            "scope": scopes, "access_type": "offline", "prompt": "select_account consent",
        }
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        if open_browser:
            webbrowser.open(url)
        srv.handle_request()
        return getattr(srv, "account_record", None)
    finally:
        srv.server_close()
        release_login_lock()
