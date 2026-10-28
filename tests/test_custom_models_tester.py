"""Unit tests for model endpoint connectivity tester."""

import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch
from antigravity_suite.models.tester import test_model_endpoint


class TestCustomModelsTester(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_endpoint_success(self, mock_urlopen):
        resp_data = {
            "choices": [{"message": {"role": "assistant", "content": "pong response"}}]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(resp_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        ok, latency, reply = test_model_endpoint(
            "http://127.0.0.1:11434/v1", "llama3", api_key="test-key"
        )
        self.assertTrue(ok)
        self.assertGreaterEqual(latency, 0.0)
        self.assertEqual(reply, "pong response")

        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "http://127.0.0.1:11434/v1/chat/completions")
        self.assertEqual(req.headers["Authorization"], "Bearer test-key")

    @patch("urllib.request.urlopen")
    def test_endpoint_http_error(self, mock_urlopen):
        err = urllib.error.HTTPError(
            "http://api.ex.com", 401, "Unauthorized", {}, MagicMock(read=lambda: b"invalid key")
        )
        mock_urlopen.side_effect = err

        ok, latency, err_msg = test_model_endpoint("http://api.ex.com", "m1")
        self.assertFalse(ok)
        self.assertIn("HTTP 401", err_msg)
        self.assertIn("invalid key", err_msg)

    @patch("urllib.request.urlopen")
    def test_endpoint_network_failure(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        ok, latency, err_msg = test_model_endpoint("http://localhost:9999", "m1")
        self.assertFalse(ok)
        self.assertIn("Connection refused", err_msg)
