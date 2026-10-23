"""
Unit tests for App & IDE data backup and deletion.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from antigravity_suite.migration.cleanup import (
    delete_all_data,
    delete_app_data,
    delete_history_data,
    delete_ide_data,
)
from antigravity_suite.migration.safety import create_safety_backup


class TestDataBackupAndCleanup(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.user_home = os.path.join(self.test_dir, "home")
        os.makedirs(self.user_home, exist_ok=True)

        self.app_cfg = os.path.join(self.user_home, ".config", "Antigravity")
        os.makedirs(self.app_cfg, exist_ok=True)
        with open(os.path.join(self.app_cfg, "app_storage.json"), "w") as f:
            f.write('{"pinnedConversations":[]}')

        self.ide_cfg = os.path.join(self.user_home, ".config", "Antigravity IDE")
        os.makedirs(self.ide_cfg, exist_ok=True)
        with open(os.path.join(self.ide_cfg, "settings.json"), "w") as f:
            f.write('{"editor.fontSize": 14}')

        self.gemini_dir = os.path.join(self.user_home, ".gemini", "antigravity")
        os.makedirs(os.path.join(self.gemini_dir, "conversations"), exist_ok=True)
        os.makedirs(os.path.join(self.gemini_dir, "brain"), exist_ok=True)
        with open(os.path.join(self.gemini_dir, "conversation_summaries.db"), "w") as f:
            f.write("mock_db_content")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("antigravity_suite.migration.safety.REAL_HOME")
    @patch("antigravity_suite.migration.safety.BACKUPS_DIR")
    def test_backup_app_category(self, mock_backups_dir, mock_real_home):
        mock_real_home.__str__.return_value = self.user_home
        mock_backups_dir.__str__.return_value = os.path.join(self.user_home, ".config", "antigravity", "backups")
        with patch("antigravity_suite.migration.safety.REAL_HOME", self.user_home), \
             patch("antigravity_suite.migration.safety.BACKUPS_DIR", os.path.join(self.user_home, ".config", "antigravity", "backups")):
            tar_path = create_safety_backup(category="app", label="test_app")
            self.assertIsNotNone(tar_path)
            self.assertTrue(os.path.isfile(tar_path))
            self.assertIn("app-test_app", os.path.basename(tar_path))

    @patch("antigravity_suite.migration.safety.REAL_HOME")
    @patch("antigravity_suite.migration.safety.BACKUPS_DIR")
    def test_backup_ide_category(self, mock_backups_dir, mock_real_home):
        with patch("antigravity_suite.migration.safety.REAL_HOME", self.user_home), \
             patch("antigravity_suite.migration.safety.BACKUPS_DIR", os.path.join(self.user_home, ".config", "antigravity", "backups")):
            tar_path = create_safety_backup(category="ide", label="test_ide")
            self.assertIsNotNone(tar_path)
            self.assertTrue(os.path.isfile(tar_path))
            self.assertIn("ide-test_ide", os.path.basename(tar_path))

    def test_delete_app_data(self):
        with patch("antigravity_suite.migration.cleanup.REAL_HOME", self.user_home), patch("subprocess.run"):
            self.assertTrue(os.path.exists(self.app_cfg))
            res = delete_app_data(backup=False)
            self.assertTrue(res)
            self.assertFalse(os.path.exists(self.app_cfg))

    def test_delete_ide_data(self):
        with patch("antigravity_suite.migration.cleanup.REAL_HOME", self.user_home), patch("subprocess.run"):
            self.assertTrue(os.path.exists(self.ide_cfg))
            res = delete_ide_data(backup=False)
            self.assertTrue(res)
            self.assertFalse(os.path.exists(self.ide_cfg))

    def test_delete_history_data(self):
        with patch("antigravity_suite.migration.cleanup.MASTER_GEMINI", self.gemini_dir):
            sum_db = os.path.join(self.gemini_dir, "conversation_summaries.db")
            self.assertTrue(os.path.isfile(sum_db))
            res = delete_history_data(backup=False)
            self.assertTrue(res)
            self.assertFalse(os.path.isfile(sum_db))
            self.assertTrue(os.path.isdir(os.path.join(self.gemini_dir, "conversations")))

    def test_delete_all_data(self):
        with patch("antigravity_suite.migration.cleanup.REAL_HOME", self.user_home), \
             patch("antigravity_suite.migration.cleanup.MASTER_GEMINI", self.gemini_dir), \
             patch("antigravity_suite.migration.cleanup.GEMINI_DIR", os.path.join(self.user_home, ".gemini")), \
             patch("antigravity_suite.migration.cleanup.ANTIGRAVITY_CONF_DIR", os.path.join(self.user_home, ".config", "antigravity")), \
             patch("subprocess.run"):
            res = delete_all_data(backup=False)
            self.assertTrue(res)
            self.assertFalse(os.path.exists(self.app_cfg))
            self.assertFalse(os.path.exists(self.ide_cfg))
