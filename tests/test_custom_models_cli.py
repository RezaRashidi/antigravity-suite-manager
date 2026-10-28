"""Unit tests for Custom Models CLI parser and dispatchers."""

import unittest
from unittest.mock import MagicMock, patch
from antigravity_suite.cli.models import build_parser, main
from antigravity_suite.cli.models_ops import op_add_provider, op_list


class TestCustomModelsCLI(unittest.TestCase):
    def test_build_parser_defaults(self):
        p = build_parser()
        args = p.parse_args([])
        self.assertEqual(args.action, "list")
        self.assertEqual(args.model, "reza")

    @patch("antigravity_suite.cli.models.op_list", return_value=0)
    def test_main_list(self, mock_list):
        code = main(["list"])
        self.assertEqual(code, 0)
        mock_list.assert_called_once()

    @patch("antigravity_suite.cli.models.op_add_provider", return_value=0)
    def test_main_add_provider(self, mock_add):
        code = main(["add-provider", "--name", "P1", "--url", "http://localhost:11434/v1"])
        self.assertEqual(code, 0)
        mock_add.assert_called_once_with("P1", "http://localhost:11434/v1", None)

    def test_main_add_provider_missing_args(self):
        code = main(["add-provider"])
        self.assertEqual(code, 1)

    @patch("antigravity_suite.cli.models.op_fetch", return_value=0)
    def test_main_fetch(self, mock_fetch):
        code = main(["fetch", "--provider", "odirect"])
        self.assertEqual(code, 0)
        mock_fetch.assert_called_once_with("odirect")

    @patch("antigravity_suite.cli.models.op_select", return_value=0)
    def test_main_select(self, mock_sel):
        code = main(["select", "--provider", "odirect", "--models", "reza,m2"])
        self.assertEqual(code, 0)
        mock_sel.assert_called_once_with("odirect", ["reza", "m2"])

    @patch("antigravity_suite.cli.models.op_test", return_value=0)
    def test_main_test_action(self, mock_test):
        code = main(["test", "--provider", "odirect", "--model", "reza"])
        self.assertEqual(code, 0)
        mock_test.assert_called_once_with("odirect", "reza")

    @patch("antigravity_suite.cli.models.op_proxy", return_value=0)
    def test_main_proxy_actions(self, mock_proxy):
        self.assertEqual(main(["proxy-status"]), 0)
        self.assertEqual(main(["proxy-start"]), 0)
        self.assertEqual(main(["proxy-stop"]), 0)
        self.assertEqual(mock_proxy.call_count, 3)

    @patch("antigravity_suite.cli.models.op_ide", return_value=0)
    def test_main_ide_actions(self, mock_ide):
        self.assertEqual(main(["apply-ide"]), 0)
        self.assertEqual(main(["restore-ide"]), 0)
        self.assertEqual(mock_ide.call_count, 2)
