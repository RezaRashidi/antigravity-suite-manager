"""OAuth HTTP Loopback Request Handler."""

from __future__ import annotations

import http.server
import urllib.parse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from antigravity_suite.multi_account.models import AccountRecord

_SUCCESS_HTML = (
    "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Connected!</title></head>"
    "<body style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;"
    "background:#0f172a;color:#f8fafc;display:flex;align-items:center;justify-content:center;"
    "height:100vh;margin:0;padding:20px;box-sizing:border-box;'>"
    "<div style='background:#1e293b;border:1px solid #334155;border-radius:12px;padding:32px;"
    "max-width:440px;width:100%;text-align:center;box-shadow:0 10px 25px rgba(0,0,0,0.5);'>"
    "<div style='width:52px;height:52px;border-radius:50%;background:rgba(34,197,94,0.15);"
    "color:#22c55e;font-size:26px;display:flex;align-items:center;justify-content:center;margin:0 auto 16px;'>✓</div>"
    "<h2 style='margin:0 0 8px;font-size:22px;color:#f8fafc;'>Connected!</h2>"
    "<p style='margin:0 0 16px;color:#94a3b8;font-size:15px;'>Successfully authenticated <b style='color:#38bdf8;'>{email}</b>.</p>"
    "<p style='margin:0;color:#64748b;font-size:13px;'>You can close this tab and return to Antigravity.</p>"
    "</div><script>setTimeout(()=>{{ try {{ window.close(); }} catch(_){{}} }}, 2500);</script>"
    "</body></html>"
)

_FAIL_HTML = (
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


class OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(url.query)
        if "code" in qs:
            from antigravity_suite.multi_account.oauth_exchange import exchange_auth_code
            code = qs["code"][0]
            self.server.auth_code = code  # type: ignore
            port = self.server.server_port
            redirect_uri = f"http://127.0.0.1:{port}/callback"
            rec: AccountRecord | None = exchange_auth_code(code, redirect_uri)
            self.server.account_record = rec  # type: ignore

            if rec:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(_SUCCESS_HTML.format(email=rec.email).encode("utf-8"))
            else:
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(_FAIL_HTML.encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass
