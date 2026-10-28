"""Unit tests for proxy daemon supervisor and status checks."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from antigravity_suite.models.proxy_daemon import (
    get_proxy_pid,
    get_proxy_pid_path,
    get_proxy_status,
    is_proxy_running,
    start_proxy_daemon,
    stop_proxy_daemon,
)


class TestCustomModelsProxy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pid_file = Path(self.tmp.name) / "proxy.pid"
        os.environ["ANTIGRAVITY_PROXY_PID_PATH"] = str(self.pid_file)

    def tearDown(self):
        os.environ.pop("ANTIGRAVITY_PROXY_PID_PATH", None)
        self.tmp.cleanup()

    def test_get_proxy_pid_stale_and_valid(self):
        self.assertIsNone(get_proxy_pid())
        # Stale non-existent PID
        self.pid_file.write_text("9999999")
        self.assertIsNone(get_proxy_pid())
        self.assertFalse(self.pid_file.exists())
        # Current valid PID
        self.pid_file.write_text(str(os.getpid()))
        self.assertEqual(get_proxy_pid(), os.getpid())

    @patch("antigravity_suite.models.proxy_daemon.is_proxy_running", return_value=True)
    def test_get_proxy_status_running(self, _mock_running):
        status = get_proxy_status(port=50999)
        self.assertTrue(status["running"])
        self.assertEqual(status["port"], 50999)

    @patch("subprocess.Popen")
    @patch("antigravity_suite.models.proxy_daemon.is_proxy_running")
    def test_start_and_stop_daemon(self, mock_running, mock_popen):
        mock_running.side_effect = [False, True, True, False]
        mock_proc = MagicMock(pid=12345)
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        started = start_proxy_daemon(port=50999, cmd=["dummy"])
        self.assertTrue(started)
        self.assertEqual(self.pid_file.read_text().strip(), "12345")

        with patch("os.kill") as mock_kill:
            stopped = stop_proxy_daemon(port=50999)
            self.assertTrue(stopped)
            mock_kill.assert_called()
