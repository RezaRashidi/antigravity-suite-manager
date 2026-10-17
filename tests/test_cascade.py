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

    def test_build_summaries_state_wire_format(self):
        import base64
        from antigravity_suite.proto.vscdb import build_summaries_state
        from antigravity_suite.proto.wire import read_varint

        fake_raw = build_cascade_summary("test-uuid-1", "Test Title", "Test Preview", 3)
        sums = {"test-uuid-1": fake_raw}
        topic_b64 = build_summaries_state(sums)
        self.assertIsInstance(topic_b64, str)

        raw = base64.b64decode(topic_b64)
        pos = 0
        decoded_map = {}
        while pos < len(raw):
            tw, pos = read_varint(raw, pos)
            tag = tw >> 3
            self.assertEqual(tag, 1)  # Topic.data is repeated Tag 1
            length, pos = read_varint(raw, pos)
            entry_bytes = raw[pos : pos + length]
            pos += length

            epos = 0
            k, v = None, None
            while epos < len(entry_bytes):
                etw, epos = read_varint(entry_bytes, epos)
                etag = etw >> 3
                elen, epos = read_varint(entry_bytes, epos)
                eval_ = entry_bytes[epos : epos + elen]
                epos += elen
                if etag == 1:
                    k = eval_.decode("utf-8")
                elif etag == 2:
                    # Row message: Tag 1 is string value (base64)
                    rpos = 0
                    while rpos < len(eval_):
                        rtw, rpos = read_varint(eval_, rpos)
                        rtag = rtw >> 3
                        rlen, rpos = read_varint(eval_, rpos)
                        rval = eval_[rpos : rpos + rlen]
                        rpos += rlen
                        if rtag == 1:
                            v = rval.decode("utf-8")
            if k and v:
                decoded_map[k] = v

        self.assertIn("test-uuid-1", decoded_map)
        inner_bin = base64.b64decode(decoded_map["test-uuid-1"])
        self.assertEqual(inner_bin, fake_raw)

    def test_update_sidebar_workspaces_state(self):
        from antigravity_suite.proto.vscdb import (
            parse_sidebar_workspaces,
            update_sidebar_workspaces_state,
        )

        initial = update_sidebar_workspaces_state(None, ["file:///home/user/PhpstormProjects/project-alpha"])
        parsed1 = parse_sidebar_workspaces(initial)
        self.assertIn("file:///home/user/PhpstormProjects/project-alpha", parsed1)

        updated = update_sidebar_workspaces_state(initial, [
            "file:///home/user/PhpstormProjects/project-alpha",
            "file:///home/user/Music/project-beta",
        ])
        parsed2 = parse_sidebar_workspaces(updated)
        self.assertIn("file:///home/user/PhpstormProjects/project-alpha", parsed2)
        self.assertIn("file:///home/user/Music/project-beta", parsed2)

    def test_normalize_workspace_uri(self):
        from antigravity_suite.history.merger import normalize_workspace_uri

        self.assertEqual(
            normalize_workspace_uri("file:///home/user/PhpstormProjects/project-alpha/backend"),
            "file:///home/user/PhpstormProjects/project-alpha",
        )
        self.assertEqual(
            normalize_workspace_uri("file:///home/user/Music/project-beta/src"),
            "file:///home/user/Music/project-beta",
        )
        self.assertEqual(
            normalize_workspace_uri('["file:///home/user/PhpstormProjects/project-alpha/memory-bank"]'),
            "file:///home/user/PhpstormProjects/project-alpha",
        )

    def test_project_id_tag18_and_tag14(self):
        from antigravity_suite.proto.wire import read_varint

        data = build_cascade_summary(
            uuid="c0a80101-0000-0000-0000-000000000001",
            title="Project Tag Test",
            summary="Testing Tag 18 and Tag 14",
            step_count=3,
            workspace_uri="file:///home/user/PhpstormProjects/project-alpha",
            project_id="7bc454c1-6ec0-4ab3-b5eb-09fb9887e76f",
        )
        parsed = parse_cascade_summary(data)
        self.assertEqual(parsed.get("project_id"), "7bc454c1-6ec0-4ab3-b5eb-09fb9887e76f")

        # Verify wire-level presence of Tag 17 submessage containing Tag 18 and Tag 14
        pos = 0
        tag17_data = None
        while pos < len(data):
            tag_wire, pos = read_varint(data, pos)
            wire_type = tag_wire & 7
            tag_num = tag_wire >> 3
            if wire_type == 2:
                length, pos = read_varint(data, pos)
                val_bytes = data[pos : pos + length]
                pos += length
                if tag_num == 17:
                    tag17_data = val_bytes
                    break
            elif wire_type == 0:
                _, pos = read_varint(data, pos)
            elif wire_type == 1:
                pos += 8
            elif wire_type == 5:
                pos += 4

        self.assertIsNotNone(tag17_data)
        sub_tags = []
        p17 = 0
        while p17 < len(tag17_data):
            tw, p17 = read_varint(tag17_data, p17)
            wt = tw & 7
            tn = tw >> 3
            if wt == 2:
                l, p17 = read_varint(tag17_data, p17)
                v = tag17_data[p17 : p17 + l]
                p17 += l
                sub_tags.append((tn, v))
            elif wt == 0:
                _, p17 = read_varint(tag17_data, p17)

        tag_nums = [t[0] for t in sub_tags]
        self.assertIn(18, tag_nums, "Tag 18 (project_id for Go CortexTrajectoryMetadata) must be present")
        self.assertIn(14, tag_nums, "Tag 14 (legacy project_id) must be present")

    def test_get_project_id_for_workspace(self):
        from antigravity_suite.history.projects import get_project_id_for_workspace

        alpha_root = "file:///home/user/PhpstormProjects/project-alpha"
        alpha_sub = "file:///home/user/PhpstormProjects/project-alpha/.github/workflows"
        root_pid = get_project_id_for_workspace(alpha_root)
        sub_pid = get_project_id_for_workspace(alpha_sub)
        self.assertIsNotNone(root_pid)
        self.assertEqual(root_pid, sub_pid)

        beta_pid = get_project_id_for_workspace("file:///home/user/Music/project-beta")
        self.assertIsNotNone(beta_pid)
        self.assertNotEqual(root_pid, beta_pid)

        gamma_pid = get_project_id_for_workspace("file:///home/user/PhpstormProjects/sample-app")
        self.assertIsNotNone(gamma_pid)
        self.assertNotEqual(beta_pid, gamma_pid)

    def test_parse_cascade_tag17_workspace_metadata(self):
        """Verifies Tag 17 Tag 1 CortexWorkspaceMetadata submessage is correctly decoded."""
        from antigravity_suite.proto.wire import encode_tag_bytes

        # Build Tag 17 with only Tag 1 CortexWorkspaceMetadata (no Tag 7, no Tag 9)
        ws_sub = bytearray()
        ws_sub += encode_tag_bytes(1, b"file:///home/user/workspace/app")
        ws_sub += encode_tag_bytes(2, b"file:///home/user/workspace/app")

        tag17_body = bytearray()
        tag17_body += encode_tag_bytes(1, bytes(ws_sub))
        tag17_body += encode_tag_bytes(18, b"project-uuid-1234")

        data = bytearray()
        data += encode_tag_bytes(1, b"Prompt message")
        data += encode_tag_bytes(17, bytes(tag17_body))

        parsed = parse_cascade_summary(bytes(data))
        self.assertEqual(parsed.get("workspace_uri"), "file:///home/user/workspace/app")
        self.assertEqual(parsed.get("project_id"), "project-uuid-1234")

    def test_parse_sidebar_workspaces_mixed_wire_types(self):
        """Verifies parse_sidebar_workspaces tolerates non-length-delimited fields without corrupting."""
        import base64
        from antigravity_suite.proto.vscdb import parse_sidebar_workspaces
        from antigravity_suite.proto.wire import encode_tag_bytes, encode_tag_uint

        valid_entry = bytearray()
        valid_entry += encode_tag_bytes(1, b"file:///home/user/app")
        valid_entry += encode_tag_bytes(2, b"dummy-row-bytes")

        payload = bytearray()
        payload += encode_tag_uint(10, 42)  # Varint Tag 10
        payload += encode_tag_bytes(1, bytes(valid_entry))  # Length-delimited entry
        payload += encode_tag_uint(12, 1)  # Varint Tag 12

        val_b64 = base64.b64encode(bytes(payload)).decode("ascii")
        parsed = parse_sidebar_workspaces(val_b64)
        self.assertIn("file:///home/user/app", parsed)


if __name__ == "__main__":
    unittest.main()

