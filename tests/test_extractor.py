"""
Unit Tests for Extractor and Title Decoding (including Persian/Unicode).
"""

import sys
import unittest
from pathlib import Path

_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from antigravity_suite.history.extractor import decode_pbtxt_string, get_annotation_title


class TestExtractor(unittest.TestCase):
    def test_decode_pbtxt_string_persian_plain(self):
        persian_text = "بررسی کد و رفع باگ‌ها"
        decoded = decode_pbtxt_string(persian_text)
        self.assertEqual(decoded, persian_text)

    def test_decode_pbtxt_string_octal_escapes(self):
        # Protobuf text format often escapes non-ASCII as octal bytes
        # 'سلام' in UTF-8 is \330\263\331\204\330\247\331\205
        escaped_octal = r"\330\263\331\204\330\247\331\205"
        decoded = decode_pbtxt_string(escaped_octal)
        self.assertEqual(decoded, "سلام")

    def test_decode_pbtxt_string_mixed(self):
        # Mixed ascii and unicode escape
        text = "Test \\u0633\\u0644\\u0627\\u0645"
        decoded = decode_pbtxt_string(text)
        self.assertEqual(decoded, "Test سلام")


    def test_decode_pbtxt_string_double_backslash(self):
        # Double backslash followed by n (e.g. Windows path or LaTeX) must preserve literal \n
        text = r"C:\\new_folder\\test.txt"
        decoded = decode_pbtxt_string(text)
        self.assertEqual(decoded, r"C:\new_folder\test.txt")

    def test_extract_conv_text_markdown_artifact_priority(self):
        import tempfile, os
        from antigravity_suite.history.extractor import extract_conv_text

        with tempfile.TemporaryDirectory() as td:
            brain_dir = os.path.join(td, "brain", "test-uuid")
            logs_dir = os.path.join(brain_dir, ".system_generated", "logs")
            os.makedirs(logs_dir, exist_ok=True)
            transcript_file = os.path.join(logs_dir, "transcript.jsonl")
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write('{"source":"USER_EXPLICIT","type":"USER_INPUT","content":"<USER_REQUEST>Raw user prompt text</USER_REQUEST>"}\n')

            # Create task.md with H1 header
            task_file = os.path.join(brain_dir, "task.md")
            with open(task_file, "w", encoding="utf-8") as f:
                f.write("# Building Authentication Microservice\nSome content\n")

            title, preview = extract_conv_text("", transcript_file)
            self.assertEqual(title, "Building Authentication Microservice")
            self.assertEqual(preview, "Raw user prompt text")

    def test_extract_conv_text_sqlite_latest_prompt(self):
        import tempfile, sqlite3
        from antigravity_suite.history.extractor import extract_conv_text
        from antigravity_suite.proto.wire import encode_tag_bytes

        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            conn = sqlite3.connect(f.name)
            cur = conn.cursor()
            cur.execute("CREATE TABLE steps (idx integer, step_type integer, step_payload blob, PRIMARY KEY(idx));")
            # Insert 10 user prompts
            for i in range(1, 11):
                prompt = f"User prompt message #{i}"
                sub = bytearray()
                sub += encode_tag_bytes(2, prompt.encode("utf-8"))
                chunk = encode_tag_bytes(1, prompt.encode("utf-8"))
                sub += encode_tag_bytes(3, bytes(chunk))
                payload = encode_tag_bytes(19, bytes(sub))
                cur.execute("INSERT INTO steps VALUES (?, 14, ?)", (i, bytes(payload)))
            conn.commit()
            conn.close()

            title, preview = extract_conv_text(f.name, "")
            self.assertEqual(title, "User prompt message #1")
            self.assertEqual(preview, "User prompt message #10")

    def test_extract_conv_text_strips_context_mentions(self):
        import tempfile, os
        from antigravity_suite.history.extractor import extract_conv_text

        with tempfile.TemporaryDirectory() as td:
            logs_dir = os.path.join(td, ".system_generated", "logs")
            os.makedirs(logs_dir, exist_ok=True)
            transcript_file = os.path.join(logs_dir, "transcript.jsonl")
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write('{"source":"USER_EXPLICIT","type":"USER_INPUT","content":"<USER_REQUEST>@[/home/reza/Downloads/minio-ansible-main/group_vars/all.yml:L2-L13]\\nبه سرور قدیمی دسترسی دارم\\nچطوری پیدا کنم</USER_REQUEST>"}\n')

            title, preview = extract_conv_text("", transcript_file)
            self.assertEqual(title, "به سرور قدیمی دسترسی دارم")
            self.assertIn("به سرور قدیمی دسترسی دارم", preview)


if __name__ == "__main__":
    unittest.main()
