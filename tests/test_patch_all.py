"""
Unit tests for Apply All Patches (patch-all) subsystem and patch preservation.
"""

import subprocess
import unittest
from pathlib import Path


class TestPatchAll(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.patch_all_sh = self.root / "bin/lib/sh/patch_all.sh"
        self.helpers_sh = self.root / "bin/lib/sh/patch_models_helpers.sh"
        self.render_py = self.root / "src/antigravity_suite/detect/control_center_render.py"
        self.dispatch_py = self.root / "src/antigravity_suite/detect/control_center_dispatch.py"
        self.patches_py = self.root / "src/antigravity_suite/detect/control_center_patches.py"

    def test_patch_all_script_bounded(self):
        self.assertTrue(self.patch_all_sh.is_file(), "patch_all.sh must exist")
        with open(self.patch_all_sh, "r", encoding="utf-8") as f:
            lines = len(f.readlines())
        self.assertLessEqual(lines, 100, f"patch_all.sh is {lines} lines (must be <= 100)")

    def test_helpers_detects_all_markers(self):
        with open(self.helpers_sh, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("ANTIGRAVITY_SUITE_SELECTOR_PATCH", content)
        self.assertIn("ACTIVE_PATCH_SELECTOR=true", content)
        self.assertIn("ACTIVE_PATCH_FORK=true", content)
        self.assertIn("ACTIVE_PATCH_OPEN_IDE=true", content)
        self.assertIn("patch_selector_app", content)
        self.assertIn("patch_fork_app", content)
        self.assertIn("patch_open_ide_app", content)

    def test_control_center_has_ap_option(self):
        with open(self.render_py, "r", encoding="utf-8") as f:
            r_content = f.read()
        self.assertIn("[AP] Apply All Patches", r_content)

        with open(self.dispatch_py, "r", encoding="utf-8") as f:
            d_content = f.read()
        self.assertIn('up in ["AP", "ALL-PATCHES", "PATCH-ALL"]', d_content)

        with open(self.patches_py, "r", encoding="utf-8") as f:
            p_content = f.read()
        self.assertIn("def handle_control_center_patch_all", p_content)
