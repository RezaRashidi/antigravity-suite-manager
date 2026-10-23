"""
Unit tests for robust Keyring detection, ghost Account 2 prevention, and IDE URI parsing.
"""

import os
import shutil
import tempfile
import unittest
from antigravity_suite.detect.clones_scan_app import scan_app_clones
from antigravity_suite.detect.clones_scan_ide import scan_ide_clones


class TestKeyringAndCloneDetection(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.local_bin = os.path.join(self.test_dir, ".local", "bin")
        self.local_apps = os.path.join(self.test_dir, ".local", "share", "applications")
        os.makedirs(self.local_bin, exist_ok=True)
        os.makedirs(self.local_apps, exist_ok=True)

        # Create basic app1 launcher
        self.app1_lnch = os.path.join(self.local_bin, "antigravity-1")
        with open(self.app1_lnch, "w") as f:
            f.write("#!/bin/bash\nexec /opt/Antigravity/antigravity --password-store=basic \"$@\"\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ghost_account2_not_detected_without_launcher(self):
        # Create an orphaned profile2 directory without launcher or desktop file
        p2 = os.path.join(self.test_dir, ".antigravity-profile2")
        os.makedirs(os.path.join(p2, ".gemini", "cache"), exist_ok=True)

        clones = scan_app_clones(real_home=self.test_dir)
        clone_ids = [c["id"] for c in clones]
        self.assertNotIn("app2", clone_ids)
        # Account 1 should be named primary 'Antigravity' when no other real accounts exist
        self.assertEqual(clones[0]["name"], "Antigravity")

    def test_account2_detected_when_launcher_exists(self):
        p2 = os.path.join(self.test_dir, ".antigravity-profile2")
        os.makedirs(os.path.join(p2, ".gemini", "cache"), exist_ok=True)
        # Create launcher for Account 2
        acc2_lnch = os.path.join(self.local_bin, "antigravity-acc2")
        with open(acc2_lnch, "w") as f:
            f.write("#!/bin/bash\nexec /opt/Antigravity/antigravity \"$@\"\n")

        clones = scan_app_clones(real_home=self.test_dir)
        clone_ids = [c["id"] for c in clones]
        self.assertIn("app2", clone_ids)

    def test_keyring_mode_normal_detected_from_launcher_flag(self):
        # Even without cache marker file, launcher with --password-store=basic must be Normal
        clones = scan_app_clones(real_home=self.test_dir)
        self.assertEqual(clones[0]["keyring_mode"], "Normal (File Storage)")

        # Verify it automatically restored the cache marker file on disk
        cache_marker = os.path.join(self.test_dir, ".gemini", "cache", "antigravity-keyring-unavailable")
        self.assertTrue(os.path.isfile(cache_marker))

    def test_ide_clones_dynamic_naming(self):
        ide_lnch = os.path.join(self.local_bin, "antigravity-ide")
        with open(ide_lnch, "w") as f: f.write("#!/bin/bash\n")
        clones = scan_ide_clones(real_home=self.test_dir)
        self.assertEqual(clones[0]["name"], "Antigravity IDE")

        p_ide2 = os.path.join(self.test_dir, ".antigravity-ide-profile-work")
        os.makedirs(p_ide2, exist_ok=True)
        clones2 = scan_ide_clones(real_home=self.test_dir)
        self.assertEqual(clones2[0]["name"], "Antigravity IDE (Primary)")


if __name__ == "__main__":
    unittest.main()
