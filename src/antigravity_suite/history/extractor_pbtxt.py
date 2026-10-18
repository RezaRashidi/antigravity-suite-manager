"""
Protobuf Text Format (.pbtxt) String Decoding.
"""

from __future__ import annotations

import re


def decode_pbtxt_string(s: str) -> str:
    """Decodes a Protobuf text format quoted string, preserving UTF-8 text and resolving escape sequences."""
    if not s or "\\" not in s:
        return (s or "").strip()

    def decode_octal(m: re.Match) -> str:
        raw_b = bytes(int(x, 8) for x in re.findall(r"\\([0-7]{1,3})", m.group(0)))
        try:
            return raw_b.decode("utf-8")
        except UnicodeDecodeError:
            return raw_b.decode("latin-1", errors="replace")

    res = re.sub(r"(?:\\[0-7]{1,3})+", decode_octal, s)
    if "\\" in res:
        try:
            res = re.sub(r"\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}", lambda m: m.group(0).encode("utf-8").decode("unicode_escape"), res)
            esc_map = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "'": "'", "\\": "\\"}
            res = re.sub(r'\\([nrt"\'\\])', lambda m: esc_map.get(m.group(1), m.group(0)), res)
        except Exception:
            pass
    return res.strip()
