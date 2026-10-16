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
                sub = encode_tag_bytes(2, prompt.encode("utf-8"))
                payload = encode_tag_bytes(19, bytes(sub))
                cur.execute("INSERT INTO steps VALUES (?, 14, ?)", (i, payload))
            conn.commit()
            conn.close()

            title, preview = extract_conv_text(f.name, "")
            self.assertEqual(title, "User prompt message #1")
            self.assertEqual(preview, "User prompt message #10")


if __name__ == "__main__":
    unittest.main()
