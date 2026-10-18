"""
Unit tests for HistoryAuditLogger and Title Sanitizer.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from antigravity_suite.history.audit import HistoryAuditLogger
from antigravity_suite.history.title_sanitizer import (
    is_raw_prompt_sentence,
    sanitize_topic_title,
)


class TestAuditAndSanitizer(unittest.TestCase):
    def test_audit_logger_records_events(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "test_audit.log"
            logger = HistoryAuditLogger(log_path=log_path)

            logger.log_title_change("conv-123", "old", "new", "test_reason")
            logger.log_workspace_change("conv-123", "ws1", "ws2", "proj-abc")
            logger.log_partition_change("conv-123", "antigravity", "antigravity-ide", "workspace_bound")
            logger.log_run_summary({"active": 10, "updated": 2})

            self.assertTrue(log_path.exists())
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 4)

            ev1 = json.loads(lines[0])
            self.assertEqual(ev1["type"], "TITLE_CHANGED")
            self.assertEqual(ev1["conv_id"], "conv-123")
            self.assertEqual(ev1["old_title"], "old")
            self.assertEqual(ev1["new_title"], "new")

            ev2 = json.loads(lines[1])
            self.assertEqual(ev2["type"], "WORKSPACE_CHANGED")

            ev3 = json.loads(lines[2])
            self.assertEqual(ev3["type"], "PARTITION_CHANGED")

            ev4 = json.loads(lines[3])
            self.assertEqual(ev4["type"], "RUN_COMPLETE")
            self.assertEqual(ev4["summary"]["active"], 10)

    def test_prompt_detection_generic(self):
        self.assertTrue(is_raw_prompt_sentence("curl -s http://example.com"))
        self.assertTrue(is_raw_prompt_sentence("first line\nsecond line"))
        self.assertTrue(is_raw_prompt_sentence("docker run -d nginx"))
        self.assertTrue(is_raw_prompt_sentence("git status -s"))

        # Clean titles should NOT be detected as prompts
        self.assertFalse(is_raw_prompt_sentence("Antigravity History Synchronization"))
        self.assertFalse(is_raw_prompt_sentence("Galera Deployment Strategy"))
        self.assertFalse(is_raw_prompt_sentence("Nginx Reverse Proxy Configuration"))

    def test_sanitize_topic_title(self):
        # Clean title preserved
        self.assertEqual(sanitize_topic_title("Database Migration Setup"), "Database Migration Setup")

        # Context tokens stripped
        self.assertEqual(sanitize_topic_title("Fix bug in @[main.py]"), "Fix bug")

        # Empty fallback to workspace name
        self.assertEqual(sanitize_topic_title("", fallback_workspace="file:///home/user/my-project"), "My Project Chat")
        self.assertEqual(sanitize_topic_title(""), "Conversation")

    def test_title_anomaly_detection(self):
        from antigravity_suite.history.audit_anomalies import detect_title_anomalies

        # Shell command prompt leak
        a1 = detect_title_anomalies("curl -s https://example.com/api")
        self.assertIn("PROMPT_LEAK_SHELL_COMMAND", a1)

        # Newline prompt leak
        a2 = detect_title_anomalies("Line 1\nLine 2")
        self.assertIn("PROMPT_LEAK_NEWLINE", a2)

        # Context mention leak
        a3 = detect_title_anomalies("Fix bug in @[src/main.py]")
        self.assertIn("UNSANITIZED_CONTEXT_MENTION", a3)

        # Regression detection
        a4 = detect_title_anomalies("Conversation", old_title="Redis Galera Migration")
        self.assertTrue(any("TITLE_REGRESSION" in a for a in a4))

        # Healthy clean title
        a5 = detect_title_anomalies("DragonflyDB Redis Optimization")
        self.assertEqual(len(a5), 0)

    def test_title_warning_logged_on_anomaly(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "test_warning_audit.log"
            logger = HistoryAuditLogger(log_path=log_path)
            logger.log_title_change("c1", "Old Good Title", "curl http://leak.com", "test")

            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            ev_warn = json.loads(lines[1])
            self.assertEqual(ev_warn["type"], "TITLE_WARNING")
            self.assertEqual(ev_warn["severity"], "HIGH")
            self.assertIn("PROMPT_LEAK_SHELL_COMMAND", ev_warn["anomalies"])


    def test_sync_journal_records_actions(self):
        from antigravity_suite.history.journal import SyncJournal
        with tempfile.TemporaryDirectory() as td:
            j_path = Path(td) / "test_journal.log"
            journal = SyncJournal(journal_path=j_path)
            journal.record_chat_action(
                conv_id="12345678-abcd-1234-abcd-1234567890ab",
                action="TITLE_UPDATED",
                title="New Clean Title",
                title_source="llm_summary",
                old_title="Conversation",
                partition="antigravity-ide",
                partition_reason="ide_workspace",
                step_count=12,
                mutations=["sqlite", "proto", "vscdb"],
            )
            self.assertTrue(j_path.exists())
            content = j_path.read_text(encoding="utf-8")
            self.assertIn("[12345678]", content)
            self.assertIn("TITLE_UPDATED", content)
            self.assertIn("'Conversation' -> 'New Clean Title'", content)
            self.assertIn("(via llm_summary)", content)
            self.assertIn("antigravity-ide", content)
            self.assertIn("Stores: [sqlite,proto,vscdb]", content)


if __name__ == "__main__":
    unittest.main()
