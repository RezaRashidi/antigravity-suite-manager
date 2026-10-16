"""
Unit Tests for Conversation Database Synthesizer.
"""

import json
import os
import sqlite3
import tempfile
import unittest
from antigravity_suite.history.synthesizer import (
    is_synthesized_db_incomplete,
    parse_step14_user_prompt,
    synthesize_db_from_transcript,
)
from antigravity_suite.proto.trajectory import parse_trajectory_metadata_blob


class TestSynthesizer(unittest.TestCase):
    def test_is_synthesized_db_incomplete_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            self.assertTrue(is_synthesized_db_incomplete(tmp.name))

    def test_synthesize_db_from_transcript_with_tools(self):
        with tempfile.TemporaryDirectory() as td:
            conv_id = "test-uuid-1234-5678-90ab-cdef12345678"
            db_path = os.path.join(td, f"{conv_id}.db")
            transcript_path = os.path.join(td, "transcript_full.jsonl")

            transcript_lines = [
                {
                    "step_index": 0,
                    "source": "USER_EXPLICIT",
                    "type": "USER_INPUT",
                    "status": "DONE",
                    "content": "<USER_REQUEST>\nFix database bug\n</USER_REQUEST>",
                },
                {
                    "step_index": 1,
                    "source": "MODEL",
                    "type": "PLANNER_RESPONSE",
                    "status": "DONE",
                    "content": "I will inspect the file.",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "name": "view_file",
                            "args": {
                                "AbsolutePath": "/home/developer/src/app.py",
                                "toolAction": "Viewing file",
                                "toolSummary": "View app.py",
                            },
                        }
                    ],
                },
                {
                    "step_index": 2,
                    "source": "MODEL",
                    "type": "VIEW_FILE",
                    "status": "DONE",
                    "content": "def main():\n    pass\n",
                },
            ]

            with open(transcript_path, "w", encoding="utf-8") as f:
                for line in transcript_lines:
                    f.write(json.dumps(line) + "\n")

            ok = synthesize_db_from_transcript(
                conv_id=conv_id,
                db_path=db_path,
                transcript_path=transcript_path,
                workspace_uri="file:///home/developer/src",
                project_id="my-project",
            )
            self.assertTrue(ok)
            self.assertFalse(is_synthesized_db_incomplete(db_path))

            # Inspect synthesized SQLite database
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            # Steps count
            steps_cnt = cur.execute("SELECT count(*) FROM steps;").fetchone()[0]
            self.assertEqual(steps_cnt, 3)

            # Step 132 metadata check
            row132 = cur.execute("SELECT step_type, metadata, step_payload FROM steps WHERE idx = 2;").fetchone()
            self.assertIsNotNone(row132)
            st_type, meta, payload = row132
            self.assertEqual(st_type, 132)
            self.assertTrue(len(meta) > 20)
            self.assertIn(b"view_file", meta)
            self.assertIn(b"view_file", payload)
            self.assertIn(b"AbsolutePath", payload)
            self.assertIn(b"/home/developer/src/app.py", payload)

            # Workspace blob check
            blob_row = cur.execute("SELECT data FROM trajectory_metadata_blob WHERE id = 'main';").fetchone()
            self.assertIsNotNone(blob_row)
            parsed_blob = parse_trajectory_metadata_blob(blob_row[0])
            self.assertEqual(parsed_blob.get("workspace_uri"), "file:///home/developer/src")
            self.assertEqual(parsed_blob.get("project_id"), "my-project")

            conn.close()

    def test_tool_arguments_quotes_preserved(self):
        import tempfile, json, sqlite3
        from pathlib import Path
        from antigravity_suite.history.synthesizer import synthesize_db_from_transcript

        conv_id = "test-quotes-preservation-1234"
        lines = [
            {"source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "Please grep for this string"},
            {"source": "MODEL", "type": "PLANNER_RESPONSE", "content": "Running grep", "tool_calls": [{"id": "call_1", "name": "grep_search", "args": {"query": "\"exact_phrase\""}}]},
            {"source": "TOOL", "type": "GREP_SEARCH", "content": "results"},
        ]
        with tempfile.TemporaryDirectory() as td:
            tf_path = Path(td) / "transcript.jsonl"
            with open(tf_path, "w") as f:
                for item in lines:
                    f.write(json.dumps(item) + "\n")

            db_path = Path(td) / f"{conv_id}.db"
            success = synthesize_db_from_transcript(conv_id, db_path, tf_path)
            self.assertTrue(success)

            conn = sqlite3.connect(db_path)
            row = conn.cursor().execute("SELECT step_payload FROM steps WHERE step_type = 132;").fetchone()
            conn.close()
            self.assertIsNotNone(row)
            # Tag 140 contains the key-value pairs; verify \"exact_phrase\" is preserved intact!
            self.assertIn(b"\"exact_phrase\"", row[0])


if __name__ == "__main__":
    unittest.main()
