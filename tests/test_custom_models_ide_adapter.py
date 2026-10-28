"""Unit tests for Antigravity IDE settings adapter."""

import json
import tempfile
import unittest
from pathlib import Path
from antigravity_suite.models.ide_adapter import (
    CLOUD_CODE_KEY,
    DEFAULT_CLOUD_CODE_URL,
    apply_ide_proxy_url,
    get_ide_backup_path,
    get_ide_proxy_url,
    restore_ide_proxy_url,
)


class TestCustomModelsIdeAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings_file = Path(self.tmp.name) / "settings.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_apply_and_restore_with_backup(self):
        initial = {"editor.fontSize": 14, CLOUD_CODE_KEY: "https://old.endpoint"}
        self.settings_file.write_text(json.dumps(initial))

        apply_ide_proxy_url("http://127.0.0.1:50999", self.settings_file)
        backup_file = get_ide_backup_path(self.settings_file)
        self.assertTrue(backup_file.is_file())
        self.assertEqual(get_ide_proxy_url(self.settings_file), "http://127.0.0.1:50999")

        # Verify backup contains initial value
        with open(backup_file, "r") as f:
            bak_json = json.load(f)
        self.assertEqual(bak_json[CLOUD_CODE_KEY], "https://old.endpoint")

        # Restore from backup
        res = restore_ide_proxy_url(self.settings_file)
        self.assertTrue(res)
        self.assertFalse(backup_file.exists())
        self.assertEqual(get_ide_proxy_url(self.settings_file), "https://old.endpoint")

    def test_apply_new_file_and_restore(self):
        apply_ide_proxy_url(DEFAULT_CLOUD_CODE_URL, self.settings_file)
        self.assertEqual(get_ide_proxy_url(self.settings_file), DEFAULT_CLOUD_CODE_URL)
        res = restore_ide_proxy_url(self.settings_file)
        self.assertTrue(res)
        self.assertIsNone(get_ide_proxy_url(self.settings_file))
