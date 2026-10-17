"""
Unit tests for the Test Data Manager and gitignored test workspace fixtures.
"""

import sqlite3
import subprocess
import unittest
from pathlib import Path

from tests.test_data_manager import (
    get_isolated_workspace,
    get_repo_root,
    get_test_data_dir,
    sync_test_data,
)


class TestTestDataManager(unittest.TestCase):
    def setUp(self):
        self.repo_root = get_repo_root()
        self.test_data_dir = get_test_data_dir()

    def test_test_data_folder_is_gitignored(self):
        """Verifies that tests/test_data and files inside are gitignored."""
        dummy_file = self.test_data_dir / "sample_check.db"
        dummy_file.touch()

        # Run git check-ignore
        res = subprocess.run(
            ["git", "check-ignore", str(dummy_file)],
            cwd=str(self.repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Expected {dummy_file} to be ignored by git")

    def test_sync_test_data_populates_valid_structures(self):
        """Verifies that sync_test_data creates valid SQLite databases and directories."""
        data_dir = sync_test_data(dest_dir=self.test_data_dir)
        self.assertTrue(data_dir.is_dir())

        # Check conversation_summaries.db
        conv_db = data_dir / "gemini" / "conversation_summaries.db"
        self.assertTrue(conv_db.is_file(), "conversation_summaries.db should exist in test_data/gemini")
        con = sqlite3.connect(f"file:{conv_db}?mode=ro", uri=True)
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cur.fetchall()]
        con.close()
        self.assertTrue(len(tables) > 0, "conversation_summaries.db should contain tables")

        # Check state.vscdb
        vscdb = data_dir / "ide" / "state.vscdb"
        self.assertTrue(vscdb.is_file(), "state.vscdb should exist in test_data/ide")
        con_vsc = sqlite3.connect(f"file:{vscdb}?mode=ro", uri=True)
        cur_vsc = con_vsc.cursor()
        cur_vsc.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable';")
        self.assertIsNotNone(cur_vsc.fetchone(), "ItemTable must exist in state.vscdb")
        con_vsc.close()

    def test_isolated_workspace_creation(self):
        """Verifies isolated workspaces stay inside gitignored test_data."""
        ws = get_isolated_workspace("test_run_1")
        self.assertTrue(ws.is_dir())
        self.assertTrue(str(ws).startswith(str(self.test_data_dir)))

        # Verify git ignores files inside isolated workspace
        ws_file = ws / "scratch.json"
        ws_file.write_text('{"key": "value"}', encoding="utf-8")
        res = subprocess.run(
            ["git", "check-ignore", str(ws_file)],
            cwd=str(self.repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Expected {ws_file} to be gitignored")


if __name__ == "__main__":
    unittest.main()
