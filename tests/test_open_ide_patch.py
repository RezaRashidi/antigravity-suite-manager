"""
Unit tests for Native Open in IDE button patcher and status detection.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from bin.lib.sh.status_inspect import check_app_open_ide


class TestOpenIdePatch(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.app_dir = os.path.join(self.test_dir, "app")
        self.dist_dir = os.path.join(self.app_dir, "dist")
        self.ide_install_dir = os.path.join(self.dist_dir, "ideInstall")
        os.makedirs(self.ide_install_dir, exist_ok=True)

        self.preload_js = os.path.join(self.dist_dir, "preload.js")
        with open(self.preload_js, "w") as f:
            f.write("// Original preload\nconst ideAPI = { isInstalled: () => false };\n")

        self.constants_js = os.path.join(self.ide_install_dir, "constants.js")
        with open(self.constants_js, "w") as f:
            f.write("function getIdeInstallPath() {\n    switch(process.platform) {\n        case 'linux':\n            return '/home/user/.local/share/antigravity-ide';\n    }\n}\n")

        self.patch_js = os.path.abspath("bin/lib/patch/patch_open_ide.js")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_patch_and_unpatch_cycle(self):
        # 1. Apply patch
        res = subprocess.run(["node", self.patch_js, self.app_dir], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        # Verify marker and content
        marker = os.path.join(self.dist_dir, "antigravity_open_ide_patch.marker")
        self.assertTrue(os.path.isfile(marker))

        with open(self.preload_js, "r") as f:
            preload_content = f.read()
        self.assertIn("OPEN_IDE_PRELOAD_START", preload_content)
        self.assertIn("showOpenIde = true", preload_content)

        with open(self.constants_js, "r") as f:
            const_content = f.read()
        self.assertIn("OPEN_IDE_CONST_START", const_content)
        self.assertIn("/opt/antigravity-ide", const_content)

        # 2. Revert / unpatch
        res_unpatch = subprocess.run(["node", self.patch_js, "--unpatch", self.app_dir], capture_output=True, text=True)
        self.assertEqual(res_unpatch.returncode, 0)
        self.assertFalse(os.path.isfile(marker))

        with open(self.preload_js, "r") as f:
            clean_preload = f.read()
        self.assertNotIn("OPEN_IDE_PRELOAD_START", clean_preload)

        with open(self.constants_js, "r") as f:
            clean_const = f.read()
        self.assertNotIn("OPEN_IDE_CONST_START", clean_const)


if __name__ == "__main__":
    unittest.main()
