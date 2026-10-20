"""OAuth loopback server for authenticating new Google accounts."""

from __future__ import annotations

import datetime
import http.server
import json
import urllib.parse
import urllib.request
import webbrowser
from typing import Optional
from antigravity_suite.multi_account.models import AccountRecord, AccountToken
from antigravity_suite.multi_account.tokens import (
    get_oauth_credentials, parse_jwt_claims
)
from antigravity_suite.multi_account.vault import save_account_to_vault


class _OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(url.query)
        if "code" in qs:
            self.server.auth_code = qs["code"][0]  # type: ignore
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h2>Connected!</h2><p>You can close this tab.</p>")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass


def exchange_auth_code(code: str, redirect_uri: str) -> Optional[AccountRecord]:
    cid, sec = get_oauth_credentials()
    payload = {
        "code": code,
        "client_id": cid,
        "client_secret": sec,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            exp_in = d.get("expires_in", 3600)
            exp_dt = (
                datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(seconds=exp_in)
            ).strftime("%Y-%m-%dT%H:%M:%S.000000+00:00")
            claims = parse_jwt_claims(d.get("id_token", ""))
            email = claims.get("email", "")
            if not email:
                return None
            rec = AccountRecord(
                email=email,
                name=claims.get("name", email.split("@")[0]),
                sub=claims.get("sub", ""),
                token=AccountToken(d.get("access_token", ""), d.get("refresh_token", ""), exp_dt),
                id_token=d.get("id_token", ""),
            )
            save_account_to_vault(rec)
            return rec
    except Exception:
        return None


def start_login_flow(open_browser: bool = True) -> Optional[AccountRecord]:
    srv = http.server.HTTPServer(("127.0.0.1", 0), _OAuthHandler)
    srv.auth_code = None  # type: ignore
    port = srv.server_port
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    cid, _ = get_oauth_credentials()
    params = {
        "client_id": cid,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid profile email https://www.googleapis.com/auth/cloud-platform",
        "access_type": "offline",
        "prompt": "select_account consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    if open_browser:
        webbrowser.open(url)
    srv.handle_request()
    srv.server_close()
    code = getattr(srv, "auth_code", None)
    return exchange_auth_code(code, redirect_uri) if code else None
