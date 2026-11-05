"""
Tests for Antigravity IDE minimum version 2.6 requirement on patches.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


class TestIdeMinVersion(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_ide = os.path.join(self.temp_dir, "opt", "antigravity-ide")
        self.app_dir = os.path.join(self.mock_ide, "resources", "app")
        os.makedirs(os.path.join(self.app_dir, "out"), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_product(self, ide_ver="2.6.0", code_ver="1.107.0"):
        p = os.path.join(self.app_dir, "product.json")
        data = {"nameLong": "Antigravity IDE", "version": code_ver}
        if ide_ver is not None:
            data["ideVersion"] = ide_ver
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_check_ide_min_version_passes_on_2_6_0_or_higher(self):
        self._write_product("2.6.0")
        cmd = f"""
        source "{_ROOT}/bin/lib/sh/env.sh"
        source "{_ROOT}/bin/lib/sh/patch_ide_helpers.sh"
        check_ide_min_version "{self.mock_ide}" "2.6.0"
        """
        res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Expected 0, got {res.returncode}: {res.stderr}")

    def test_check_ide_min_version_passes_on_2_7_0(self):
        self._write_product("2.7.0")
        cmd = f"""
        source "{_ROOT}/bin/lib/sh/env.sh"
        source "{_ROOT}/bin/lib/sh/patch_ide_helpers.sh"
        check_ide_min_version "{self.mock_ide}" "2.6.0"
        """
        res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Expected 0, got {res.returncode}: {res.stderr}")

    def test_check_ide_min_version_blocks_older_versions(self):
        self._write_product("2.5.5")
        cmd = f"""
        source "{_ROOT}/bin/lib/sh/env.sh"
        source "{_ROOT}/bin/lib/sh/patch_ide_helpers.sh"
        check_ide_min_version "{self.mock_ide}" "2.6.0"
        """
        res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("v2.6.0+ is required", res.stderr + res.stdout)

    def test_check_ide_min_version_blocks_missing_ide_version(self):
        # Only upstream code version 1.107.0 without ideVersion
        self._write_product(ide_ver=None, code_ver="1.107.0")
        cmd = f"""
        source "{_ROOT}/bin/lib/sh/env.sh"
        source "{_ROOT}/bin/lib/sh/patch_ide_helpers.sh"
        check_ide_min_version "{self.mock_ide}" "2.6.0"
        """
        res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)

    def test_js_selector_patch_enforces_min_version(self):
        self._write_product("2.5.5")
        js_path = str(_ROOT / "bin" / "antigravity-selector-patch.js")
        res = subprocess.run(["node", js_path, "--ide", self.mock_ide], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("v2.6.0+", res.stderr + res.stdout)

    def test_js_fork_patch_enforces_min_version(self):
        self._write_product("2.5.5")
        js_path = str(_ROOT / "bin" / "antigravity-fork-patch.js")
        res = subprocess.run(["node", js_path, "--ide", self.mock_ide], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("v2.6.0+", res.stderr + res.stdout)


if __name__ == "__main__":
    unittest.main()
