"""Loopback HTTP Reverse Proxy Server for Antigravity Language Server."""

from __future__ import annotations

import http.client
import http.server
import ssl
import urllib.parse
from antigravity_suite.multi_account.proxy_core import (
    DEFAULT_UPSTREAM, extract_cascade_id, prepare_upstream_headers,
    resolve_account_token
)


class MultiAccountProxyHandler(http.server.BaseHTTPRequestHandler):
    upstream_url: str = DEFAULT_UPSTREAM

    def do_POST(self):
        self._proxy_request("POST")

    def do_GET(self):
        if self.path == "/healthz":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok","proxy":"antigravity-multi-account"}')
            return
        self._proxy_request("GET")

    def _proxy_request(self, method: str):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b""
        cid = extract_cascade_id(body)
        token = resolve_account_token(cid)
        up_parsed = urllib.parse.urlparse(self.upstream_url)
        headers = prepare_upstream_headers(
            dict(self.headers), token, up_parsed.netloc, body_len=len(body)
        )

        try:
            ctx = ssl.create_default_context()
            conn = http.client.HTTPSConnection(up_parsed.netloc, port=443, context=ctx, timeout=60)
            conn.request(method, self.path, body=body if body else None, headers=headers)
            resp = conn.getresponse()

            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in ["connection"]:
                    self.send_header(k, v)
            self.end_headers()

            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
            conn.close()
        except Exception as e:
            if not self.wfile.closed:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(f'{{"error":"Upstream proxy failed: {e}"}}'.encode("utf-8"))

    def log_message(self, *args):
        pass


def run_proxy_server(port: int = 41999, upstream: str = DEFAULT_UPSTREAM) -> http.server.ThreadingHTTPServer:
    MultiAccountProxyHandler.upstream_url = upstream
    return http.server.ThreadingHTTPServer(("127.0.0.1", port), MultiAccountProxyHandler)
