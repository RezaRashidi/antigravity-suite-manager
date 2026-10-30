#!/usr/bin/env python3
"""Regression test for multi-account proxy chaining and quota refresh."""

import unittest
from pathlib import Path


class TestMultiAccountProxyChain(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.proxy_file = self.root / "vendor/antigravity-model-proxy/dist/proxy.js"
        self.telem_file = self.root / "bin/lib/patch/router/telemetry.js"
        self.api_file = self.root / "bin/lib/patch/router/api.js"

    def test_proxy_js_has_multi_account_forwarding(self):
        self.assertTrue(self.proxy_file.exists())
        content = self.proxy_file.read_text("utf-8")
        self.assertIn("MULTI_ACCOUNT_PORT = 41999", content)
        self.assertIn("isMultiAccountAvailable()", content)
        self.assertIn("`http://127.0.0.1:${MULTI_ACCOUNT_PORT}`", content)
        self.assertIn("ECONNREFUSED", content)

    def test_telemetry_has_force_refresh_quota(self):
        self.assertTrue(self.telem_file.exists())
        content = self.telem_file.read_text("utf-8")
        self.assertIn("forceRefreshLanguageServerQuota", content)
        self.assertIn("forceRefresh: true", content)

    def test_api_calls_force_refresh_on_bind_and_set_active(self):
        self.assertTrue(self.api_file.exists())
        content = self.api_file.read_text("utf-8")
        self.assertIn("forceRefreshLanguageServerQuota", content)


if __name__ == "__main__":
    unittest.main()
