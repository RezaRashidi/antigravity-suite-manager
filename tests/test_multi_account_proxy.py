"""Unit tests for Multi-Account proxy server and headers."""
import threading
import unittest
from antigravity_suite.multi_account.proxy_core import extract_cascade_id, prepare_upstream_headers
from antigravity_suite.multi_account.proxy_server import run_proxy_server
from antigravity_suite.multi_account.service import is_proxy_running

class TestMultiAccountProxy(unittest.TestCase):
    def test_extract_cascade_id(self):
        self.assertEqual(extract_cascade_id(b'{"cascadeId":"cas-123"}'), "cas-123")
        self.assertEqual(extract_cascade_id(b'{"conversationId":"conv-456"}'), "conv-456")
        self.assertIsNone(extract_cascade_id(b""))

    def test_prepare_upstream_headers(self):
        in_h = {"Host": "127.0.0.1:41999", "Authorization": "old", "Content-Length": "5"}
        out_h = prepare_upstream_headers(in_h, "new_tok", "cloudcode.google.com")
        self.assertEqual(out_h["Host"], "cloudcode.google.com")
        self.assertEqual(out_h["Authorization"], "Bearer new_tok")
        self.assertNotIn("Content-Length", out_h)

    def test_proxy_server_healthz(self):
        server = run_proxy_server(port=41997)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            self.assertTrue(is_proxy_running(port=41997))
        finally:
            server.shutdown()
            server.server_close()
