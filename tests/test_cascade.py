"""
Unit Tests for Cascade Summary and Trajectory Metadata Protobuf Serialization.
"""

import unittest
from antigravity.proto.cascade import build_cascade_summary, parse_cascade_summary
from antigravity.proto.trajectory import (
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


if __name__ == "__main__":
    unittest.main()
