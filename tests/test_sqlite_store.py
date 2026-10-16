"""
Unit Tests for SQLite Store upsert_summary metadata preservation and connection management.
"""

import tempfile
import unittest
import sqlite3
from antigravity_suite.history.models import ConversationSummary
from antigravity_suite.history.sqlite_store import ensure_summaries_schema, upsert_summary


class TestSqliteStore(unittest.TestCase):
    def test_upsert_summary_preserves_authentic_metadata(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            conn = sqlite3.connect(f.name)
            ensure_summaries_schema(conn)

            # Insert initial rich authentic row
            initial = ConversationSummary(
                conversation_id="conv-1234",
                title="Original Title",
                preview="Original Preview",
                step_count=5,
                last_modified_time="2026-10-15T10:00:00+00:00",
                workspace_uris="file:///home/user/project",
                status="CASCADE_RUN_STATUS_RUNNING",
                source="IDE",
                project_id="proj-42",
                agent_name="code-expert",
                parent_conversation_id="parent-99",
                nesting_depth=2,
                battle_id="battle-7",
                winning_conversation_id="winner-1",
                not_fully_idle=True,
                killed=True,
                last_user_input_time="2026-10-15T09:50:00+00:00",
                last_user_input_step_index=4,
                app_data_dir="custom_app",
                group_id="group-1",
            )
            upsert_summary(conn, initial)
            conn.commit()

            # Now perform an incremental update with default/empty values for metadata
            update = ConversationSummary(
                conversation_id="conv-1234",
                title="Updated Title",
                preview="Updated Preview",
                step_count=10,
                last_modified_time="2026-10-16T10:00:00+00:00",
                workspace_uris="",
                project_id="",
            )
            upsert_summary(conn, update)
            conn.commit()

            cur = conn.cursor()
            row = cur.execute("SELECT title, preview, step_count, status, not_fully_idle, killed, source, project_id, parent_conversation_id, group_id FROM conversation_summaries WHERE conversation_id = 'conv-1234';").fetchone()
            conn.close()

            # Computed fields were updated
            self.assertEqual(row[0], "Updated Title")
            self.assertEqual(row[1], "Updated Preview")
            self.assertEqual(row[2], 10)

            # Authentic metadata fields were NOT clobbered by default values!
            self.assertEqual(row[3], "CASCADE_RUN_STATUS_RUNNING")
            self.assertEqual(row[4], 1)  # not_fully_idle retained True/1
            self.assertEqual(row[5], 1)  # killed retained True/1
            self.assertEqual(row[6], "IDE")
            self.assertEqual(row[7], "proj-42")
            self.assertEqual(row[8], "parent-99")
            self.assertEqual(row[9], "group-1")


if __name__ == "__main__":
    unittest.main()
