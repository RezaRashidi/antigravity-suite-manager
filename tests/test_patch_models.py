"""
Unit tests for In-App Custom Models Settings UI patcher and runtime scripts.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestPatchModels(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.deploy_mjs = self.root / "vendor/antigravity-model-proxy/scripts/deploy.mjs"
        self.preload_js = self.root / "vendor/antigravity-model-proxy/dist/customPreload.js"
        self.patch_sh = self.root / "bin/lib/sh/patch_models.sh"
        self.helpers_sh = self.root / "bin/lib/sh/patch_models_helpers.sh"

    def test_patch_scripts_exist_and_bounded(self):
        self.assertTrue(self.deploy_mjs.is_file(), "deploy.mjs must exist")
        self.assertTrue(self.preload_js.is_file(), "customPreload.js must exist")
        self.assertTrue(self.patch_sh.is_file(), "patch_models.sh must exist")
        self.assertTrue(self.helpers_sh.is_file(), "patch_models_helpers.sh must exist")

        with open(self.patch_sh, "r", encoding="utf-8") as f:
            lines = len(f.readlines())
        self.assertLessEqual(lines, 100, f"patch_models.sh is {lines} lines (must be <= 100)")

        with open(self.helpers_sh, "r", encoding="utf-8") as f:
            lines = len(f.readlines())
        self.assertLessEqual(lines, 100, f"patch_models_helpers.sh is {lines} lines (must be <= 100)")

    def test_custom_preload_contains_in_app_ui_markers(self):
        with open(self.preload_js, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("agy-custom-models-section", content)
        self.assertIn("injectCustomModelsSection", content)
        self.assertIn("openModelModal", content)
        self.assertIn("body.vscode-light #agy-custom-models-section", content)
        self.assertIn("--agy-bg", content)
        self.assertIn("openConfigureGateway", content)
        self.assertIn("openAddGatewayModal", content)
        self.assertIn("openDiscoverGatewayModels", content)
        self.assertIn("autoImportFreeModels", content)
        self.assertNotIn("window.confirm", content)

    def test_deploy_check_runs_cleanly(self):
        orig_asar = Path("/opt/Antigravity-x64/resources/app.asar.orig")
        if not orig_asar.is_file():
            self.skipTest("Clean app.asar.orig not found on system")

        temp_dir = tempfile.mkdtemp()
        try:
            target_asar = Path(temp_dir) / "app.asar"
            shutil.copyfile(orig_asar, target_asar)
            res = subprocess.run(
                ["node", str(self.deploy_mjs), "--check", "--resources", temp_dir],
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, f"deploy.mjs --check failed: {res.stderr}")
            self.assertIn("CHECK PASSED", res.stdout)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
