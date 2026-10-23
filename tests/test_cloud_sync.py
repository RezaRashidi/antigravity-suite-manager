"""
Unit tests for Antigravity Cloud Sync: WAL flushing, workspace provisioning, and conflict resolution.
"""

import os
import shutil
import sqlite3
import tempfile
import unittest

from antigravity_suite.cloud.config_manager import load_remote_name, save_remote_name
from antigravity_suite.cloud.conflict import evaluate_sync_action, fork_local_divergence, get_db_metrics
from antigravity_suite.cloud.pull_ingest import ingest_staged_conversations
from antigravity_suite.cloud.rclone_client import is_rclone_installed, list_rclone_remotes
from antigravity_suite.cloud.sqlite_wal import checkpoint_single_db, flush_all_wal
from antigravity_suite.cloud.workspace_guard import ensure_workspace_exists, resolve_local_workspace_path


def _create_test_db(db_path: str, max_step: int = 5, uri: str = "") -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE steps (idx integer primary key, step_type integer);")
    for i in range(max_step + 1):
        cur.execute("INSERT INTO steps (idx, step_type) VALUES (?, 0);", (i,))
    cur.execute("CREATE TABLE trajectory_metadata_blob (id text primary key, data blob);")
    if uri:
        # Simple mock blob containing file URI
        cur.execute("INSERT INTO trajectory_metadata_blob (id, data) VALUES ('main', ?);", (uri.encode("utf-8"),))
    conn.commit()
    conn.close()


class TestCloudSync(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.conv_dir = os.path.join(self.test_dir, "conversations")
        self.brain_dir = os.path.join(self.test_dir, "brain")
        os.makedirs(self.conv_dir, exist_ok=True)
        os.makedirs(self.brain_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sqlite_wal_checkpoint(self):
        db_p = os.path.join(self.conv_dir, "chat1.db")
        _create_test_db(db_p, max_step=3)
        # Touch a mock -wal file
        with open(f"{db_p}-wal", "w") as f:
            f.write("mock wal data")
        self.assertTrue(os.path.isfile(f"{db_p}-wal"))
        res = checkpoint_single_db(db_p)
        self.assertTrue(res)

        total_flushed = flush_all_wal(self.conv_dir)
        self.assertGreaterEqual(total_flushed, 1)

    def test_workspace_guard_resolution_and_creation(self):
        ws_target = os.path.join(self.test_dir, "auto_projects", "my_api")
        uri = f"file://{ws_target}"
        resolved = resolve_local_workspace_path(uri, real_home=self.test_dir)
        self.assertEqual(resolved, ws_target)

        # Folder does not exist yet
        self.assertFalse(os.path.exists(ws_target))
        created = ensure_workspace_exists(ws_target)
        self.assertTrue(created)
        self.assertTrue(os.path.isdir(ws_target))
        # Calling again should return False since it already exists
        self.assertFalse(ensure_workspace_exists(ws_target))

    def test_conflict_evaluation_fast_forward_and_local_ahead(self):
        local_db = os.path.join(self.conv_dir, "chat2.db")
        incoming_db = os.path.join(self.test_dir, "incoming.db")

        # Incoming has 10 steps, local has 5
        _create_test_db(local_db, max_step=5)
        _create_test_db(incoming_db, max_step=10)

        apply, reason = evaluate_sync_action(local_db, incoming_db)
        self.assertTrue(apply)
        self.assertEqual(reason, "fast_forward")

        # Local has 12 steps, incoming has 10 (Local is ahead)
        _create_test_db(local_db, max_step=12)
        apply, reason = evaluate_sync_action(local_db, incoming_db)
        self.assertFalse(apply)
        self.assertEqual(reason, "local_ahead")

    def test_divergence_forking(self):
        local_db = os.path.join(self.conv_dir, "diverge_test.db")
        _create_test_db(local_db, max_step=4)
        b_dir = os.path.join(self.brain_dir, "diverge_test")
        os.makedirs(b_dir, exist_ok=True)

        forked = fork_local_divergence(local_db, self.brain_dir)
        self.assertTrue(os.path.isfile(forked))
        self.assertIn("fork", forked)

    def test_config_manager(self):
        os.environ.pop("ANTIGRAVITY_CLOUD_REMOTE", None)
        saved = save_remote_name("test-vault:")
        self.assertEqual(saved, "test-vault")
        loaded = load_remote_name()
        self.assertEqual(loaded, "test-vault")


if __name__ == "__main__":
    unittest.main()
