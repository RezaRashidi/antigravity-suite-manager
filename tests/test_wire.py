"""
Unit Tests for Protobuf Wire Format Encoding and Decoding.
"""

import unittest
from antigravity.proto.wire import (
    encode_annotations_field,
    encode_tag_bytes,
    encode_tag_uint,
    encode_timestamp_field,
    encode_varint,
    extract_entries_from_proto,
    extract_pure_binary_summary,
    read_varint,
)


class TestProtobufWire(unittest.TestCase):
    def test_varint_roundtrip(self):
        test_values = [0, 1, 127, 128, 255, 300, 16384, 2097151, 2147483647]
        for val in test_values:
            encoded = encode_varint(val)
            decoded, pos = read_varint(encoded, 0)
            self.assertEqual(val, decoded)
            self.assertEqual(pos, len(encoded))

    def test_encode_tag_bytes(self):
        tag = 3
        data = b"Hello, Antigravity!"
        encoded = encode_tag_bytes(tag, data)
        tag_wire, pos = read_varint(encoded, 0)
        self.assertEqual(tag_wire >> 3, tag)
        self.assertEqual(tag_wire & 7, 2)
        length, pos = read_varint(encoded, pos)
        self.assertEqual(length, len(data))
        self.assertEqual(encoded[pos : pos + length], data)

    def test_encode_tag_uint(self):
        tag = 6
        val = 42
        encoded = encode_tag_uint(tag, val)
        tag_wire, pos = read_varint(encoded, 0)
        self.assertEqual(tag_wire >> 3, tag)
        self.assertEqual(tag_wire & 7, 0)
        decoded, _ = read_varint(encoded, pos)
        self.assertEqual(decoded, val)

    def test_encode_timestamp_field(self):
        iso_str = "2026-10-15T20:30:00+00:00"
        encoded = encode_timestamp_field(iso_str)
        self.assertTrue(len(encoded) > 0)
        self.assertEqual(encoded[0], 0x08)  # Tag 1 wire type 0

    def test_encode_annotations_field(self):
        encoded = encode_annotations_field(step_count=10, last_user_step=9)
        self.assertTrue(len(encoded) > 0)

    def test_extract_pure_binary_summary_plain(self):
        raw = b"\x0a\x04test"
        result = extract_pure_binary_summary(raw)
        self.assertEqual(result, raw)

    def test_extract_entries_from_proto(self):
        uuid_str = "12345678-1234-1234-1234-123456789abc"
        payload = b"\x08\x01\x12\x04data"
        entry = bytearray()
        entry += encode_tag_bytes(1, uuid_str.encode("utf-8"))
        entry += encode_tag_bytes(2, payload)
        proto_data = encode_tag_bytes(1, bytes(entry))

        entries = extract_entries_from_proto(proto_data)
        self.assertIn(uuid_str, entries)
        self.assertEqual(entries[uuid_str], payload)


if __name__ == "__main__":
    unittest.main()
