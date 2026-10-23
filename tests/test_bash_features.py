"""
Unit tests for bash library and patch integration.
"""

import os
import sys
import unittest
from pathlib import Path

_BIN_DIR = str(Path(__file__).resolve().parent.parent / "bin")


class TestBashLibraryAndPatches(unittest.TestCase):
    def test_unpatch_rtl_functions_exist(self):
        """Verifies unpatch rtl functions exist in unpatch_rtl.sh."""
        sh_path = os.path.join(_BIN_DIR, "lib", "sh", "unpatch_rtl.sh")
        with open(sh_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("unpatch_rtl_app()", code)
        self.assertIn("unpatch_rtl_ide()", code)
        self.assertIn("unpatch_rtl_all()", code)

    def test_uninstall_apps_functions_exist(self):
        """Verifies uninstallation routines exist in modular scripts."""
        for name in ["uninstall_apps.sh", "uninstall_app.sh", "uninstall_ide.sh"]:
            sh_path = os.path.join(_BIN_DIR, "lib", "sh", name)
            self.assertTrue(os.path.isfile(sh_path))
        with open(os.path.join(_BIN_DIR, "lib", "sh", "uninstall_apps.sh"), "r") as f:
            code = f.read()
        self.assertIn("uninstall_all()", code)
        self.assertIn("uninstall_menu_interactive()", code)

    def test_update_reapplies_detected_patches(self):
        """Verifies update_all detects active patches and re-applies them."""
        detect_path = os.path.join(_BIN_DIR, "lib", "sh", "suite_update_detect.sh")
        with open(detect_path, "r", encoding="utf-8") as f:
            d_code = f.read()
        self.assertIn("detect_active_app_patches()", d_code)
        self.assertIn("detect_active_ide_patches()", d_code)
        self.assertIn("HAD_APP_SELECTOR", d_code)

        sh_path = os.path.join(_BIN_DIR, "lib", "sh", "suite_update.sh")
        with open(sh_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn('if [ "$HAD_APP_SELECTOR" = true ]; then', code)
        self.assertIn('if [ "$HAD_IDE_SELECTOR" = true ]; then', code)
        self.assertIn('if [ "$HAD_APP_FORK" = true ]; then', code)
        self.assertIn('if [ "$HAD_IDE_FORK" = true ]; then', code)

    def test_cli_dispatch_and_parse(self):
        """Verifies clean-data, uninstall, unpatch-rtl CLI commands are recognized."""
        parse_sh = os.path.join(_BIN_DIR, "lib", "sh", "cli_parse.sh")
        with open(parse_sh, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("unpatch-rtl)", code)
        self.assertIn("clean-data|delete-data|purge-data)", code)
        self.assertIn("uninstall)", code)

        dispatch_sh = os.path.join(_BIN_DIR, "lib", "sh", "cli_dispatch.sh")
        with open(dispatch_sh, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("clean-data|delete-data|purge-data)", code)
        self.assertIn("uninstall)", code)
        self.assertIn("unpatch-rtl)", code)

    def test_menu_actions_and_options(self):
        """Verifies menu has options for clean data, uninstall, and unpatches."""
        menu_sh = os.path.join(_BIN_DIR, "lib", "sh", "menu.sh")
        with open(menu_sh, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("Clean / Delete Antigravity Data", code)
        self.assertIn("Uninstall Antigravity Apps", code)
        self.assertIn("Revert / Unpatch RTL Patcher", code)
        self.assertIn("Revert / Unpatch F5 Manual Sync Backend Reload Patch", code)

        dispatcher_sh = os.path.join(_BIN_DIR, "lib", "sh", "menu_dispatcher.sh")
        with open(dispatcher_sh, "r", encoding="utf-8") as f:
            d_code = f.read()
        self.assertIn("menu_action_clean_data", d_code)
