"""OAuth loopback server for authenticating new Google accounts."""

from __future__ import annotations

import datetime
import http.server
import json
import os
import signal
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from typing import Optional
from antigravity_suite.multi_account.lock import acquire_pid_lock, release_pid_lock
from antigravity_suite.multi_account.models import AccountRecord, AccountToken
from antigravity_suite.multi_account.tokens import (
    get_oauth_credentials, parse_jwt_claims
)
from antigravity_suite.multi_account.vault import get_accounts_dir, save_account_to_vault

acquire_login_lock = acquire_pid_lock
release_login_lock = release_pid_lock


class _OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(url.query)
        if "code" in qs:
            code = qs["code"][0]
            self.server.auth_code = code  # type: ignore
            port = self.server.server_port
            redirect_uri = f"http://127.0.0.1:{port}/callback"

            # Immediately exchange token while user is on this request
            rec = exchange_auth_code(code, redirect_uri)
            self.server.account_record = rec  # type: ignore

            if rec:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html = (
                    "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Connected!</title></head>"
                    "<body style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;"
                    "background:#0f172a;color:#f8fafc;display:flex;align-items:center;justify-content:center;"
                    "height:100vh;margin:0;padding:20px;box-sizing:border-box;'>"
                    "<div style='background:#1e293b;border:1px solid #334155;border-radius:12px;padding:32px;"
                    "max-width:440px;width:100%;text-align:center;box-shadow:0 10px 25px rgba(0,0,0,0.5);'>"
                    "<div style='width:52px;height:52px;border-radius:50%;background:rgba(34,197,94,0.15);"
                    "color:#22c55e;font-size:26px;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;'>✓</div>"
                    f"<h2 style='margin:0 0 8px;font-size:22px;color:#f8fafc;'>Connected!</h2>"
                    f"<p style='margin:0 0 16px;color:#94a3b8;font-size:15px;'>Successfully authenticated <b style='color:#38bdf8;'>{rec.email}</b>.</p>"
                    "<p style='margin:0;color:#64748b;font-size:13px;'>You can close this tab and return to Antigravity.</p>"
                    "</div>"
                    "<script>setTimeout(()=>{ try { window.close(); } catch(_){} }, 2500);</script>"
                    "</body></html>"
                )
                self.wfile.write(html.encode("utf-8"))
            else:
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html = (
                    "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Authentication Failed</title></head>"
                    "<body style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;"
                    "background:#0f172a;color:#f8fafc;display:flex;align-items:center;justify-content:center;"
                    "height:100vh;margin:0;padding:20px;box-sizing:border-box;'>"
                    "<div style='background:#1e293b;border:1px solid #334155;border-radius:12px;padding:32px;"
                    "max-width:440px;width:100%;text-align:center;box-shadow:0 10px 25px rgba(0,0,0,0.5);'>"
                    "<div style='width:52px;height:52px;border-radius:50%;background:rgba(239,68,68,0.15);"
                    "color:#ef4444;font-size:26px;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;'>✕</div>"
                    "<h2 style='margin:0 0 8px;font-size:22px;color:#f8fafc;'>Authentication Failed</h2>"
                    "<p style='margin:0 0 16px;color:#94a3b8;font-size:15px;'>Failed to exchange Google OAuth authorization code.</p>"
                    "<p style='margin:0;color:#64748b;font-size:13px;'>Check proxy / internet connection and try again.</p>"
                    "</div></body></html>"
                )
                self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass


def exchange_auth_code(code: str, redirect_uri: str) -> Optional[AccountRecord]:
    import sys
    import os
    cid, sec = get_oauth_credentials()
    if not cid or not sec:
        print("[OAuth] Error: Missing Google OAuth Client ID or Secret", file=sys.stderr)
        return None

    # Forward ide_http_proxy if standard proxy env is unset
    if not os.environ.get("https_proxy") and os.environ.get("ide_http_proxy"):
        os.environ["https_proxy"] = os.environ["ide_http_proxy"]
    if not os.environ.get("http_proxy") and os.environ.get("ide_http_proxy"):
        os.environ["http_proxy"] = os.environ["ide_http_proxy"]

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
        with urllib.request.urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            exp_in = d.get("expires_in", 3600)
            exp_dt = (
                datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(seconds=exp_in)
            ).strftime("%Y-%m-%dT%H:%M:%S.000000+00:00")
            claims = parse_jwt_claims(d.get("id_token", ""))
            email = claims.get("email", "")
            if not email:
                print("[OAuth] Error: No email claim in id_token", file=sys.stderr)
                return None
            rec = AccountRecord(
                email=email,
                name=claims.get("name", email.split("@")[0]),
                sub=claims.get("sub", ""),
                token=AccountToken(d.get("access_token", ""), d.get("refresh_token", ""), exp_dt),
                id_token=d.get("id_token", ""),
            )
            save_account_to_vault(rec)
            print(f"[OAuth] Successfully saved account {email} to vault", file=sys.stderr)

            # Notify local router proxy immediately to invalidate cache and refresh UI
            try:
                notify_req = urllib.request.Request("http://127.0.0.1:41999/api/multi-account/state?refresh=1", method="GET")
                with urllib.request.urlopen(notify_req, timeout=2) as _:
                    pass
            except Exception:
                pass

            return rec
    except Exception as e:
        print(f"[OAuth] Token exchange failed: {e}", file=sys.stderr)
        return None


def start_login_flow(open_browser: bool = True, timeout: int = 180) -> Optional[AccountRecord]:
    acquire_login_lock()
    srv = http.server.HTTPServer(("127.0.0.1", 0), _OAuthHandler)
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
            "client_id": cid,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "access_type": "offline",
            "prompt": "select_account consent",
        }
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        if open_browser:
            webbrowser.open(url)
        srv.handle_request()
        return getattr(srv, "account_record", None)
    finally:
        srv.server_close()
        release_login_lock()
