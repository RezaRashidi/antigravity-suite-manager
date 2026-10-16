"""
Unit Tests for Extractor and Title Decoding (including Persian/Unicode).
"""

import unittest
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


if __name__ == "__main__":
    unittest.main()
