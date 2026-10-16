"""
Unit Tests for Cascade Summary and Trajectory Metadata Protobuf Serialization.
"""

import sys
import unittest
from pathlib import Path

_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from antigravity_suite.proto.cascade import build_cascade_summary, parse_cascade_summary
from antigravity_suite.proto.trajectory import (
    build_trajectory_metadata_blob,
    parse_trajectory_metadata_blob,
)


class TestCascadeAndTrajectory(unittest.TestCase):
    def test_cascade_summary_roundtrip(self):
        uuid = "b8ce61c5-e433-43af-ac03-e29bcb50c347"
        title = "Optimize Network Configuration"
        summary = "Refactored routing tables and proxy rules."
        step_count = 15

        data = build_cascade_summary(
            uuid=uuid,
            title=title,
            summary=summary,
            step_count=step_count,
            workspace_uri="file:///home/developer/projects/net",
            project_id="proj-42",
        )
        self.assertTrue(len(data) > 0)

        parsed = parse_cascade_summary(data)
        self.assertEqual(parsed.get("trajectory_id"), uuid)
        self.assertEqual(parsed.get("title"), title)
        self.assertEqual(parsed.get("summary"), summary)
        self.assertEqual(parsed.get(2), step_count)
        self.assertEqual(parsed.get("workspace_uri"), "file:///home/developer/projects/net")
        self.assertEqual(parsed.get("project_id"), "proj-42")

    def test_trajectory_metadata_blob_roundtrip(self):
        conv_id = "5bd4cfc0-38b3-4013-8a66-bf3aecfc5693"
        ws_uri = "file:///home/user/workspace/app"
        proj_id = "custom-project-id"

        blob = build_trajectory_metadata_blob(
            conv_id=conv_id,
            workspace_uri=ws_uri,
            project_id=proj_id,
        )
        self.assertTrue(len(blob) > 0)

        parsed = parse_trajectory_metadata_blob(blob)
        self.assertEqual(parsed.get("workspace_folder"), ws_uri)
        self.assertEqual(parsed.get("git_root"), ws_uri)
        self.assertEqual(parsed.get("root_conversation_id"), conv_id)
        self.assertEqual(parsed.get("workspace_uri"), ws_uri)
        self.assertEqual(parsed.get("project_id"), proj_id)


    def test_timestamps_and_year1_detection(self):
        uuid = "b8ce61c5-e433-43af-ac03-e29bcb50c347"
        data = build_cascade_summary(
            uuid=uuid,
            title="Timestamp Test",
            summary="Testing timestamps",
            step_count=5,
            last_modified_iso="2026-08-14 18:05:41.000000+00:00",
            created_iso="2026-08-01 10:00:00.000000+00:00",
            last_user_input_iso="2026-08-14 17:30:00.000000+00:00",
        )
        self.assertNotIn(b"\x80\x92\xb8\xc3\x98\xfe\xff\xff\xff\x01", data)
        parsed = parse_cascade_summary(data)
        self.assertFalse(parsed.get("has_bad_timestamp", False))
        self.assertEqual(parsed.get("last_modified_iso"), "2026-08-14 18:05:41.000000+00:00")
        self.assertEqual(parsed.get("created_iso"), "2026-08-01 10:00:00.000000+00:00")
        self.assertEqual(parsed.get("last_user_input_iso"), "2026-08-14 17:30:00.000000+00:00")

        # Corrupted data with Year 1 bytes
        corrupted = data + b"\x08\x80\x92\xb8\xc3\x98\xfe\xff\xff\xff\x01"
        parsed_corrupt = parse_cascade_summary(corrupted)
        self.assertTrue(parsed_corrupt.get("has_bad_timestamp"))

    def test_synchronize_master_summaries_heals_year1_and_preserves_title(self):
        import shutil
        import sqlite3
        import tempfile
        from antigravity_suite.history.merger import synchronize_master_summaries, SyncStats
        from antigravity_suite.history.sqlite_store import ensure_summaries_schema

        temp_dir = Path(tempfile.mkdtemp())
        try:
            master_sum_db = temp_dir / "conversation_summaries.db"
            master_conv_dir = temp_dir / "conversations"
            master_conv_dir.mkdir(parents=True)
            master_brain_dir = temp_dir / "brain"
            master_brain_dir.mkdir(parents=True)
            master_proto = temp_dir / "master.pb"

            bad_varint = b"\x80\x92\xb8\xc3\x98\xfe\xff\xff\xff\x01"
            good_proto = build_cascade_summary(
                "11111111-2222-3333-4444-555555555555",
                "Authentic Title",
                "Authentic Preview",
                5,
            )
            corrupt_proto = good_proto + bad_varint

            conn = sqlite3.connect(str(master_sum_db))
            ensure_summaries_schema(conn)
            conn.execute(
                """
                INSERT INTO conversation_summaries (conversation_id, title, preview, step_count, last_modified_time, raw_summary, last_user_input_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("11111111-2222-3333-4444-555555555555", "", "", 5, "0001-01-01 00:00:00.000000+00:00", corrupt_proto, "0001-01-01 00:00:00.000000+00:00"),
            )
            conn.commit()
            conn.close()

            stats = SyncStats()
            con, all_sums = synchronize_master_summaries(
                temp_dir, master_conv_dir, master_brain_dir, master_sum_db, master_proto, stats
            )

            cur = con.cursor()
            row = cur.execute(
                "SELECT conversation_id, title, preview, last_modified_time, last_user_input_time, raw_summary FROM conversation_summaries WHERE conversation_id = ?",
                ("11111111-2222-3333-4444-555555555555",),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[1], "Authentic Title")
            self.assertEqual(row[2], "Authentic Preview")
            self.assertFalse(row[3].startswith("0001-"))
            self.assertFalse(row[4].startswith("0001-"))
            self.assertNotIn(bad_varint, row[5])
            con.close()
        finally:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
