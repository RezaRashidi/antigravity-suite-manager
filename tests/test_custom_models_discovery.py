"""Unit tests for remote model catalog discovery."""

import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch
from antigravity_suite.models.discovery import fetch_models, get_discovery_urls


class TestCustomModelsDiscovery(unittest.TestCase):
    def test_get_discovery_urls(self):
        self.assertEqual(
            get_discovery_urls("http://localhost:11434"),
            ["http://localhost:11434/models", "http://localhost:11434/v1/models"],
        )
        self.assertEqual(
            get_discovery_urls("http://localhost:11434/v1"),
            ["http://localhost:11434/v1/models"],
        )
        self.assertEqual(
            get_discovery_urls("http://localhost:11434/models"),
            ["http://localhost:11434/models"],
        )

    @patch("urllib.request.urlopen")
    def test_fetch_models_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({"data": [{"id": "gpt-4"}]}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = fetch_models("http://api.example.com", api_key="secret", headers={"X-Test": "1"})
        self.assertEqual(res, {"data": [{"id": "gpt-4"}]})
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.headers["Authorization"], "Bearer secret")
        self.assertEqual(req.headers["X-test"], "1")

    @patch("urllib.request.urlopen")
    def test_fetch_models_404_fallback(self, mock_urlopen):
        err_404 = urllib.error.HTTPError("http://example.com/models", 404, "Not Found", {}, None)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({"models": [{"name": "llama3"}]}).encode("utf-8")

        mock_urlopen.side_effect = [err_404, MagicMock(__enter__=MagicMock(return_value=mock_resp))]
        res = fetch_models("http://example.com")
        self.assertIn("models", res)
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("urllib.request.urlopen")
    def test_fetch_models_fatal_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError("http://ex.com", 500, "Server Error", {}, None)
        with self.assertRaises(urllib.error.HTTPError):
            fetch_models("http://ex.com")
