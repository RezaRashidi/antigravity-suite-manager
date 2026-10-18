"""
Low-Level Varint and Wire Tag Encoders and Decoders.
"""

from __future__ import annotations

from typing import Tuple


def encode_varint(n: int) -> bytes:
    """Encodes an integer into standard Protobuf Varint wire format."""
    out = bytearray()
    val = n & 0xFFFFFFFFFFFFFFFF if n < 0 else n
    while val > 0x7F:
        out.append((val & 0x7F) | 0x80)
        val >>= 7
    out.append(val & 0x7F)
    return bytes(out)


def read_varint(b: bytes, pos: int) -> Tuple[int, int]:
    """Reads a Varint from buffer `b` starting at `pos`. Returns (value, next_pos)."""
    val, shift = 0, 0
    while pos < len(b):
        byte = b[pos]
        pos += 1
        val |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return val, pos


def encode_tag_bytes(tag: int, b: bytes) -> bytes:
    """Encodes a Length-Delimited field (Wire Type 2: (tag << 3) | 2)."""
    return encode_varint((tag << 3) | 2) + encode_varint(len(b)) + b


def encode_tag_uint(tag: int, n: int) -> bytes:
    """Encodes a Varint field (Wire Type 0: tag << 3)."""
    return encode_varint(tag << 3) + encode_varint(n)
