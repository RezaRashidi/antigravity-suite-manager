"""
Unit tests for Antigravity App & IDE Downgrade subsystem.
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

_BIN_DIR = str(Path(__file__).resolve().parent.parent / "bin")
_RESOLVER = os.path.join(_BIN_DIR, "lib", "sh", "downgrade_resolver.py")


class TestDowngradeResolver(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, os.path.join(_BIN_DIR, "lib", "sh"))

    def test_resolver_script_exists_and_executable(self):
        self.assertTrue(os.path.isfile(_RESOLVER))
        self.assertTrue(os.access(_RESOLVER, os.X_OK))

    def test_version_normalization_and_sorting(self):
        import downgrade_resolver as dr
        self.assertEqual(dr.normalize_version("v2.30.0"), "2.30.0")
        self.assertEqual(dr.normalize_version(" 2.31.0 "), "2.31.0")
        self.assertEqual(dr.normalize_version("V2.6.0"), "2.6.0")

        versions = ["2.31.0", "2.6.0", "2.30.0", "2.29.1", "2.5.5"]
        sorted_vers = sorted(versions, key=dr.version_tuple, reverse=True)
        self.assertEqual(sorted_vers, ["2.31.0", "2.30.0", "2.29.1", "2.6.0", "2.5.5"])

    def test_resolve_exact_app_and_ide_versions(self):
        import downgrade_resolver as dr
        app_ver, app_url = dr.resolve_release("app", "2.30.0")
        self.assertEqual(app_ver, "2.30.0")
        self.assertIn("antigravity-hub/2.30.0-", app_url)
        self.assertTrue(app_url.endswith(".tar.gz"))

        ide_ver, ide_url = dr.resolve_release("ide", "2.5.5")
        self.assertEqual(ide_ver, "2.5.5")
        self.assertIn("2.5.5-", ide_url)
        self.assertTrue(ide_url.endswith(".tar.gz"))

    def test_resolve_previous_version(self):
        import downgrade_resolver as dr
        # Prior to 2.31.0 should be 2.30.0
        prev_app_ver, _ = dr.resolve_release("app", "prev", current_ver="2.31.0")
        self.assertEqual(prev_app_ver, "2.30.0")

        # Prior to 2.6.0 should be 2.5.5
        prev_ide_ver, _ = dr.resolve_release("ide", "previous", current_ver="2.6.0")
        self.assertEqual(prev_ide_ver, "2.5.5")

    def test_resolve_direct_url(self):
        import downgrade_resolver as dr
        custom_url = "https://custom.host/releases/2.28.0/Antigravity.tar.gz"
        ver, url = dr.resolve_release("app", custom_url)
        self.assertEqual(ver, "2.28.0")
        self.assertEqual(url, custom_url)

    def test_resolver_cli_list_and_resolve(self):
        res_list = subprocess.run(
            [sys.executable, _RESOLVER, "list", "app"],
            capture_output=True, text=True, check=True
        )
        lines = [line for line in res_list.stdout.strip().split("\n") if line]
        self.assertGreaterEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("2."))
        self.assertTrue(any("2.31.0|" in line for line in lines))

        res_resolve = subprocess.run(
            [sys.executable, _RESOLVER, "resolve", "app", "2.30.0"],
            capture_output=True, text=True, check=True
        )
        self.assertTrue(res_resolve.stdout.startswith("2.30.0|"))


class TestDowngradeBashIntegration(unittest.TestCase):
    def test_bash_syntax_all_modified_scripts(self):
        scripts = [
            os.path.join(_BIN_DIR, "lib", "sh", "downgrade.sh"),
            os.path.join(_BIN_DIR, "lib", "sh", "package_install.sh"),
            os.path.join(_BIN_DIR, "lib", "sh", "cli_flags.sh"),
            os.path.join(_BIN_DIR, "lib", "sh", "cli_parse.sh"),
            os.path.join(_BIN_DIR, "lib", "sh", "cli_dispatch.sh"),
            os.path.join(_BIN_DIR, "lib", "sh", "cli_dispatch_helpers.sh"),
            os.path.join(_BIN_DIR, "lib", "sh", "menu.sh"),
            os.path.join(_BIN_DIR, "lib", "sh", "menu_dispatcher.sh"),
            os.path.join(_BIN_DIR, "lib", "sh", "help.sh"),
            os.path.join(_BIN_DIR, "lib", "sh", "help_options.sh"),
            os.path.join(_BIN_DIR, "manage-antigravity.sh"),
        ]
        for s in scripts:
            self.assertTrue(os.path.isfile(s), f"Missing script: {s}")
            r = subprocess.run(["bash", "-n", s], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"Bash syntax error in {s}: {r.stderr}")

    def test_downgrade_functions_exist(self):
        sh_path = os.path.join(_BIN_DIR, "lib", "sh", "downgrade.sh")
        with open(sh_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("downgrade_app()", code)
        self.assertIn("downgrade_ide()", code)
        self.assertIn("downgrade_all()", code)
        self.assertIn("downgrade_interactive_or_target()", code)
        self.assertIn("ALLOW_DOWNGRADE=true", code)
        self.assertIn("detect_active_app_patches", code)
        self.assertIn("detect_active_ide_patches", code)

    def test_cli_parsing_downgrade_commands(self):
        manage_sh = os.path.join(_BIN_DIR, "manage-antigravity.sh")
        # Test help includes downgrade
        r_help = subprocess.run(["bash", manage_sh, "--help"], capture_output=True, text=True)
        self.assertEqual(r_help.returncode, 0)
        self.assertIn("downgrade", r_help.stdout)
        self.assertIn("downgrade app 2.30.0", r_help.stdout)

        # Test CLI parse recognizes downgrade command in non-interactive dry mode
        test_cmd = (
            f"source {_BIN_DIR}/lib/sh/env.sh; "
            f"source {_BIN_DIR}/lib/sh/cli_flags.sh; "
            f"source {_BIN_DIR}/lib/sh/cli_parse.sh; "
            "parse_cli_args downgrade app 2.30.0 -y; "
            'echo "$COMMAND|$SUB_COMMAND|$TARGET_DOWNGRADE_VER|$NON_INTERACTIVE"'
        )
        r_parse = subprocess.run(["bash", "-c", test_cmd], capture_output=True, text=True)
        self.assertEqual(r_parse.returncode, 0)
        self.assertEqual(r_parse.stdout.strip(), "downgrade|app|2.30.0|true")

    def test_menu_options_updated(self):
        menu_sh = os.path.join(_BIN_DIR, "lib", "sh", "menu.sh")
        with open(menu_sh, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("45) Downgrade Antigravity App or IDE to Previous Version", code)

        dispatcher_sh = os.path.join(_BIN_DIR, "lib", "sh", "menu_dispatcher.sh")
        with open(dispatcher_sh, "r", encoding="utf-8") as f:
            d_code = f.read()
        self.assertIn("45) downgrade_interactive_or_target ;;", d_code)


if __name__ == "__main__":
    unittest.main()
