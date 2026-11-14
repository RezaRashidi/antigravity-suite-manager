"""
Unit tests for Antigravity X11 BaseWindow / WebContentsView Bounds Patcher.
"""

import os
import shutil
import subprocess
import tempfile
import unittest


SAMPLE_UTILS_JS = """function createHub() {
    baseWin.contentView.addChildView(curtainView);
    baseWin.contentView.addChildView(hubWcv);
    const syncHubViewBounds = () => {
        if (!baseWin.isDestroyed?.() && !hubWcv.webContents?.isDestroyed?.()) {
            const [width, height] = baseWin.getContentSize();
            curtainView.setBounds({ x: 0, y: 0, width, height });
            hubWcv.setBounds({ x: 0, y: 0, width, height });
        }
    };
    syncHubViewBounds();
    baseWin.on('resize', syncHubViewBounds);
    win.on('closed', () => {
        win.off?.('resize', syncHubViewBounds);
    });
}
"""

SAMPLE_UTILS_V2321_JS = """function initializeHub() {
    let win;
    let syncHubViewBounds;
    if (builtInBrowser) {
        baseWin.contentView.addChildView(clipView ?? curtainView);
        baseWin.contentView.addChildView(hubWcv);
        syncHubViewBounds = () => {
            if (!baseWin.isDestroyed?.() && !hubWcv.webContents?.isDestroyed?.()) {
                const [width, height] = baseWin.getContentSize();
                curtainView?.setBounds({ x: 0, y: 0, width, height });
                hubWcv.setBounds({ x: 0, y: 0, width, height });
            }
        };
        syncHubViewBounds();
        baseWin.on('resize', syncHubViewBounds);
        win = baseWin;
    }
    if (syncHubViewBounds) {
        win.off?.('resize', syncHubViewBounds);
    }
}
"""


class TestWindowBoundsPatch(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.app_dir = os.path.join(self.test_dir, "app")
        self.dist_dir = os.path.join(self.app_dir, "dist")
        os.makedirs(self.dist_dir, exist_ok=True)
        self.utils_js = os.path.join(self.dist_dir, "utils.js")
        with open(self.utils_js, "w", encoding="utf-8") as f:
            f.write(SAMPLE_UTILS_JS)
        self.patch_js = os.path.abspath("bin/lib/patch/patch_window_bounds.js")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_patch_idempotent_and_unpatch_cycle(self):
        for _ in range(2):
            res = subprocess.run(["node", self.patch_js, self.app_dir], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

        marker = os.path.join(self.dist_dir, "antigravity_window_bounds_patch.marker")
        self.assertTrue(os.path.isfile(marker))

        with open(self.utils_js, "r", encoding="utf-8") as f:
            patched = f.read()
        self.assertEqual(patched.count("WINDOW_BOUNDS_PATCH_START"), 1)
        self.assertEqual(patched.count("WINDOW_BOUNDS_CLEANUP_START"), 1)

        # Verify patched runtime settles lagged X11 getContentSize() on maximize/resize
        runtime_check = (
            patched
            + """
let curSize = [900, 600];
let hubBounds = { x: 0, y: 0, width: 0, height: 0 };
let curtainBounds = { x: 0, y: 0, width: 0, height: 0 };
const listeners = new Map();
const win = {
    isDestroyed: () => false,
    getContentSize: () => curSize,
    on: (ev, fn) => { if (!listeners.has(ev)) listeners.set(ev, new Set()); listeners.get(ev).add(fn); },
    off: (ev, fn) => listeners.get(ev)?.delete(fn),
    contentView: { addChildView: () => {} },
};
const baseWin = win;
const curtainView = { setBounds: (b) => { curtainBounds = b; } };
const hubWcv = {
    webContents: { isDestroyed: () => false },
    getBounds: () => hubBounds,
    setBounds: (b) => { hubBounds = b; },
};
createHub();
curSize = [1952, 1204];
for (const fn of (listeners.get('resize') || [])) fn();
setTimeout(() => { curSize = [1920, 1162]; }, 10);
setTimeout(() => {
    console.log(JSON.stringify({ hubBounds, curtainBounds }));
    for (const fn of (listeners.get('closed') || [])) fn();
    if ((listeners.get('maximize')?.size || 0) !== 0) process.exit(2);
}, 120);
"""
        )
        run_res = subprocess.run(["node", "-e", runtime_check], capture_output=True, text=True, check=True)
        self.assertIn('"width":1920,"height":1162', run_res.stdout)

        # Verify unpatch restores exact original code and removes marker
        res_unpatch = subprocess.run(["node", self.patch_js, "--unpatch", self.app_dir], capture_output=True, text=True)
        self.assertEqual(res_unpatch.returncode, 0, res_unpatch.stderr)
        self.assertFalse(os.path.isfile(marker))
        with open(self.utils_js, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), SAMPLE_UTILS_JS)

    def test_patch_app_v2321_layout_cycle(self):
        with open(self.utils_js, "w", encoding="utf-8") as f:
            f.write(SAMPLE_UTILS_V2321_JS)

        for _ in range(2):
            res = subprocess.run(["node", self.patch_js, self.app_dir], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

        marker = os.path.join(self.dist_dir, "antigravity_window_bounds_patch.marker")
        self.assertTrue(os.path.isfile(marker))

        with open(self.utils_js, "r", encoding="utf-8") as f:
            patched = f.read()
        self.assertEqual(patched.count("WINDOW_BOUNDS_PATCH_START"), 1)
        self.assertEqual(patched.count("WINDOW_BOUNDS_CLEANUP_START"), 1)
        self.assertIn("curtainView?.setBounds?.(bounds)", patched)

        res_unpatch = subprocess.run(["node", self.patch_js, "--unpatch", self.app_dir], capture_output=True, text=True)
        self.assertEqual(res_unpatch.returncode, 0, res_unpatch.stderr)
        self.assertFalse(os.path.isfile(marker))
        with open(self.utils_js, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), SAMPLE_UTILS_V2321_JS)

    def test_menu_and_control_center_expose_window_bounds(self):
        with open("bin/lib/sh/menu.sh", encoding="utf-8") as f:
            menu_sh = f.read()
        with open("bin/lib/sh/menu_dispatcher.sh", encoding="utf-8") as f:
            menu_disp = f.read()
        with open("src/antigravity_suite/detect/control_center_render.py", encoding="utf-8") as f:
            cc_render = f.read()
        with open("src/antigravity_suite/detect/control_center_dispatch.py", encoding="utf-8") as f:
            cc_disp = f.read()
        with open("src/antigravity_suite/detect/configure_unified_menu.py", encoding="utf-8") as f:
            uni_menu = f.read()
        with open("src/antigravity_suite/detect/configure_unified.py", encoding="utf-8") as f:
            uni_cfg = f.read()
        with open("src/antigravity_suite/detect/unified_patches.py", encoding="utf-8") as f:
            uni_disp = f.read()

        self.assertIn("46) Apply X11 Window Bounds Fix Patch", menu_sh)
        self.assertIn("47) Revert / Unpatch X11 Window Bounds Fix", menu_sh)
        self.assertIn("46) FORCE_INSTALL=true patch_window_bounds_app ;;", menu_disp)
        self.assertIn("47) unpatch_window_bounds_app ;;", menu_disp)
        self.assertIn("[WB] X11 Window Bounds Fix", cc_render)
        self.assertIn("handle_control_center_window_bounds_patch", cc_disp)
        self.assertIn("[WB] X11 Window Bounds Fix", uni_menu)
        self.assertIn('"WB"', uni_cfg)
        self.assertIn("handle_unified_patch_window_bounds", uni_disp)


if __name__ == "__main__":
    unittest.main()
