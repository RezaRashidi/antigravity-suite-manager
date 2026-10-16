"""
Unit tests for HistoryBackupManager (automated pre-merge backup and restore).
"""

import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from antigravity_suite.history.backup import BackupEntry, HistoryBackupManager


class TestHistoryBackupManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.home = Path(self.test_dir) / "user_home"
        self.home.mkdir(parents=True)

        self.master_app_dir = self.home / ".gemini" / "antigravity"
        self.master_app_dir.mkdir(parents=True)

        # 1. Create a dummy conversation_summaries.db with WAL mode
        self.master_db = self.master_app_dir / "conversation_summaries.db"
        con = sqlite3.connect(str(self.master_db))
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute(
            """
            CREATE TABLE conversation_summaries (
                conversation_id TEXT PRIMARY KEY,
                title TEXT,
                step_count INTEGER
            );
            """
        )
        con.execute("INSERT INTO conversation_summaries VALUES ('c-123', 'Initial Title', 5);")
        con.commit()
        con.close()

        # 2. Create master protobuf file
        self.master_proto = self.master_app_dir / "agyhub_summaries_proto.pb"
        with open(self.master_proto, "wb") as f:
            f.write(b"sample_proto_bytes_1234567890")

        # 3. Create annotations directory
        self.master_anno = self.master_app_dir / "annotations"
        self.master_anno.mkdir(parents=True)
        with open(self.master_anno / "c-123.pbtxt", "w", encoding="utf-8") as f:
            f.write('title: "Initial Title"\n')

        # 4. Create dummy state.vscdb
        self.vscdb_path = self.home / "vscdb_storage" / "state.vscdb"
        self.vscdb_path.parent.mkdir(parents=True)
        v_con = sqlite3.connect(str(self.vscdb_path))
        v_con.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT);")
        v_con.execute(
            "INSERT INTO ItemTable VALUES ('antigravityUnifiedStateSync', 'eyJhbGciOiJIUzI1NiJ9');"
        )
        v_con.commit()
        v_con.close()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_backup_and_list(self):
        """Tests that create_pre_merge_backup captures all components into snapshot."""
        entry = HistoryBackupManager.create_pre_merge_backup(
            effective_master=self.master_app_dir,
            candidate_vscdbs=[self.vscdb_path],
            user_home=self.home,
            description="Test backup",
        )
        self.assertIsNotNone(entry)
        self.assertTrue(entry.backup_id.endswith("_pre_merge"))
        self.assertIn("conversation_summaries.db", entry.files)
        self.assertIn("agyhub_summaries_proto.pb", entry.files)
        self.assertIn("annotations", entry.files)
        self.assertIn("vscdb_keys.json", entry.files)
        self.assertEqual(entry.vscdb_entries_count, 1)

        # Verify listing
        backups = HistoryBackupManager.list_backups(user_home=self.home)
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].backup_id, entry.backup_id)

    def test_restore_backup_roundtrip(self):
        """Tests that restore_backup successfully rolls back modified state."""
        # 1. Take backup of initial state
        entry = HistoryBackupManager.create_pre_merge_backup(
            effective_master=self.master_app_dir,
            candidate_vscdbs=[self.vscdb_path],
            user_home=self.home,
            description="Pre-modification backup",
        )
        self.assertIsNotNone(entry)

        # 2. Corrupt / modify live state
        con = sqlite3.connect(str(self.master_db))
        con.execute("UPDATE conversation_summaries SET title='Corrupted Title', step_count=999;")
        con.commit()
        con.close()

        with open(self.master_proto, "wb") as f:
            f.write(b"corrupted_bytes")

        with open(self.master_anno / "c-123.pbtxt", "w", encoding="utf-8") as f:
            f.write('title: "Corrupted Title"\n')

        v_con = sqlite3.connect(str(self.vscdb_path))
        v_con.execute("UPDATE ItemTable SET value='corrupted_vscdb';")
        v_con.commit()
        v_con.close()

        # 3. Perform restore
        res = HistoryBackupManager.restore_backup(entry.backup_id, user_home=self.home)
        self.assertTrue(res)

        # 4. Verify live database restored
        con = sqlite3.connect(str(self.master_db))
        row = con.execute("SELECT title, step_count FROM conversation_summaries WHERE conversation_id='c-123';").fetchone()
        con.close()
        self.assertEqual(row[0], "Initial Title")
        self.assertEqual(row[1], 5)

        # 5. Verify protobuf restored
        with open(self.master_proto, "rb") as f:
            self.assertEqual(f.read(), b"sample_proto_bytes_1234567890")

        # 6. Verify annotations restored
        with open(self.master_anno / "c-123.pbtxt", "r", encoding="utf-8") as f:
            self.assertIn("Initial Title", f.read())

        # 7. Verify vscdb restored
        v_con = sqlite3.connect(str(self.vscdb_path))
        v_row = v_con.execute("SELECT value FROM ItemTable WHERE key='antigravityUnifiedStateSync';").fetchone()
        v_con.close()
        self.assertEqual(v_row[0], "eyJhbGciOiJIUzI1NiJ9")

    def test_prune_backups(self):
        """Tests that older backups beyond max_backups are pruned."""
        backup_root = HistoryBackupManager.get_backup_root(self.home)
        for i in range(5):
            d = backup_root / f"backup_{i}"
            d.mkdir(parents=True)
            with open(d / "manifest.json", "w") as mf:
                json.dump({"backup_id": f"backup_{i}"}, mf)

        self.assertEqual(len(list(backup_root.iterdir())), 5)
        HistoryBackupManager.prune_backups(backup_root, max_keep=3)
        self.assertEqual(len(list(backup_root.iterdir())), 3)


if __name__ == "__main__":
    unittest.main()
