"""
Unit tests for standalone Prompt Input Typing Performance Patcher (App & IDE).
"""

import os
import shutil
import subprocess
import tempfile
import unittest


SAMPLE_APP_UTILS_JS = """function attachRenderer(win) {
    win.webContents.on('dom-ready', () => {
        console.log('ready');
    });
    win.webContents.on('did-finish-load', () => {
        console.log('loaded');
    });
}
"""

SAMPLE_IDE_RTL_CLIENT_JS = """(function () {
    const core = {
        updateDir(el) {
            return el;
        }
    };
    window.__antigravityRtlCore = core;
})();
"""


class TestTypingPerfPatch(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.app_dir = os.path.join(self.test_dir, "app")
        self.dist_dir = os.path.join(self.app_dir, "dist")
        os.makedirs(self.dist_dir, exist_ok=True)
        self.utils_js = os.path.join(self.dist_dir, "utils.js")
        with open(self.utils_js, "w", encoding="utf-8") as f:
            f.write(SAMPLE_APP_UTILS_JS)

        self.ide_dir = os.path.join(self.test_dir, "ide")
        self.ide_out_dir = os.path.join(self.ide_dir, "resources", "app", "out")
        os.makedirs(self.ide_out_dir, exist_ok=True)
        self.ide_rtl_js = os.path.join(self.ide_out_dir, "antigravity-rtl-client.js")
        with open(self.ide_rtl_js, "w", encoding="utf-8") as f:
            f.write(SAMPLE_IDE_RTL_CLIENT_JS)

        self.patch_js = os.path.abspath("bin/lib/patch/patch_typing_perf.js")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_app_patch_idempotent_and_unpatch_cycle(self):
        for _ in range(2):
            res = subprocess.run(["node", self.patch_js, self.app_dir], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

        marker = os.path.join(self.dist_dir, "antigravity_typing_perf_patch.marker")
        fix_js = os.path.join(self.dist_dir, "typing_perf_fix.js")
        self.assertTrue(os.path.isfile(marker))
        self.assertTrue(os.path.isfile(fix_js))

        with open(self.utils_js, "r", encoding="utf-8") as f:
            patched = f.read()
        self.assertEqual(patched.count("AGY_TYPING_PERF_START"), 1)
        self.assertIn("typing_perf_fix.js", patched)

        res_unpatch = subprocess.run(["node", self.patch_js, "--unpatch", self.app_dir], capture_output=True, text=True)
        self.assertEqual(res_unpatch.returncode, 0, res_unpatch.stderr)
        self.assertFalse(os.path.isfile(marker))
        self.assertFalse(os.path.isfile(fix_js))
        with open(self.utils_js, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), SAMPLE_APP_UTILS_JS)

    def test_ide_patch_idempotent_and_unpatch_cycle(self):
        for _ in range(2):
            res = subprocess.run(["node", self.patch_js, "--ide", self.ide_dir], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

        marker = os.path.join(self.ide_out_dir, "antigravity_ide_typing_perf_patch.marker")
        self.assertTrue(os.path.isfile(marker))

        with open(self.ide_rtl_js, "r", encoding="utf-8") as f:
            patched = f.read()
        self.assertEqual(patched.count("AGY_TYPING_PERF_START"), 1)
        self.assertIn("_agyWrapped", patched)

        res_unpatch = subprocess.run(["node", self.patch_js, "--ide", "--unpatch", self.ide_dir], capture_output=True, text=True)
        self.assertEqual(res_unpatch.returncode, 0, res_unpatch.stderr)
        self.assertFalse(os.path.isfile(marker))
        with open(self.ide_rtl_js, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), SAMPLE_IDE_RTL_CLIENT_JS)

    def test_cli_menu_and_control_center_expose_typing_perf(self):
        files = {
            "menu_sh": "bin/lib/sh/menu.sh",
            "menu_disp": "bin/lib/sh/menu_dispatcher.sh",
            "cli_flags": "bin/lib/sh/cli_flags.sh",
            "cli_parse": "bin/lib/sh/cli_parse.sh",
            "cli_disp": "bin/lib/sh/cli_dispatch.sh",
            "patch_all": "bin/lib/sh/patch_all.sh",
            "upd_det": "bin/lib/sh/suite_update_detect.sh",
            "cc_render": "src/antigravity_suite/detect/control_center_render.py",
            "cc_disp": "src/antigravity_suite/detect/control_center_dispatch.py",
            "uni_menu": "src/antigravity_suite/detect/configure_unified_menu.py",
            "uni_cfg": "src/antigravity_suite/detect/configure_unified.py",
            "uni_disp": "src/antigravity_suite/detect/unified_patches.py",
        }
        contents = {}
        for k, p in files.items():
            with open(p, encoding="utf-8") as f:
                contents[k] = f.read()

        self.assertIn("48) Apply Prompt Input Typing Performance Patch", contents["menu_sh"])
        self.assertIn("49) Revert / Unpatch Prompt Input Typing Performance Patch", contents["menu_sh"])
        self.assertIn("48) FORCE_INSTALL=true patch_typing_perf ;;", contents["menu_disp"])
        self.assertIn("49) unpatch_typing_perf ;;", contents["menu_disp"])
        self.assertIn("patch-typing", contents["cli_flags"])
        self.assertIn("patch-typing", contents["cli_parse"])
        self.assertIn("dispatch_typing_perf", contents["cli_disp"])
        self.assertIn("patch_typing_perf_app", contents["patch_all"])
        self.assertIn("patch_typing_perf_ide", contents["patch_all"])
        self.assertIn("HAD_APP_TYPING_PERF", contents["upd_det"])
        self.assertIn("HAD_IDE_TYPING_PERF", contents["upd_det"])
        self.assertIn("[TP] Typing Performance Fix", contents["cc_render"])
        self.assertIn("handle_control_center_typing_perf_patch", contents["cc_disp"])
        self.assertIn("[TP] Typing Performance Fix", contents["uni_menu"])
        self.assertIn('"TP"', contents["uni_cfg"])
        self.assertIn("handle_unified_patch_typing_perf", contents["uni_disp"])


if __name__ == "__main__":
    unittest.main()
