"""
Unit tests for Antigravity IDE checksum integrity synchronizer.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from antigravity_suite.patch.ide_checksums import (
    compute_file_checksum,
    find_ide_product_json,
    sync_ide_checksums,
    verify_ide_checksums,
)


class TestIdeChecksums(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.app_dir = self.root / "resources" / "app"
        self.out_dir = self.app_dir / "out"
        self.out_dir.mkdir(parents=True)

        self.f1 = self.out_dir / "test1.js"
        self.f1.write_text("console.log('original');", encoding="utf-8")
        self.h1 = compute_file_checksum(self.f1)

        self.product = self.app_dir / "product.json"
        self.product.write_text(
            json.dumps({"checksums": {"test1.js": self.h1}}),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_find_product_json(self):
        found = find_ide_product_json(self.root)
        self.assertEqual(found, self.product)
        self.assertIsNone(find_ide_product_json(self.root / "invalid"))

    def test_verify_checksums_clean(self):
        res = verify_ide_checksums(self.root)
        self.assertIn("test1.js", res)
        expected, actual, is_match = res["test1.js"]
        self.assertTrue(is_match)
        self.assertEqual(expected, actual)

    def test_sync_checksums_after_patch(self):
        # Modify file (simulating RTL patch or custom button)
        self.f1.write_text("console.log('patched');", encoding="utf-8")
        res = verify_ide_checksums(self.root)
        self.assertFalse(res["test1.js"][2])

        # Run sync
        updated, total = sync_ide_checksums(self.root)
        self.assertEqual(updated, 1)
        self.assertEqual(total, 1)

        # Verify now matches
        res_after = verify_ide_checksums(self.root)
        self.assertTrue(res_after["test1.js"][2])

        # Second sync should do nothing
        updated2, _ = sync_ide_checksums(self.root)
        self.assertEqual(updated2, 0)


if __name__ == "__main__":
    unittest.main()
