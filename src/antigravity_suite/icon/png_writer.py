"""
Pure-Python PNG encoding and RGBA bitmap resampling.
"""

from __future__ import annotations

import os
import struct
import zlib


def write_png(w: int, h: int, rgba_data: bytearray, out_path: str) -> None:
    """Encodes RGBA byte buffer into standard PNG file."""
    stride = 1 + w * 4
    raw = bytearray(h * stride)
    for y in range(h):
        raw[y * stride] = 0
        raw[y * stride + 1 : (y + 1) * stride] = rgba_data[y * w * 4 : (y + 1) * w * 4]

    def _chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(_chunk(b'IHDR', ihdr))
        f.write(_chunk(b'IDAT', idat))
        f.write(_chunk(b'IEND', b''))


def resample_raw(src_data: bytearray, src_w: int, src_h: int, dst_w: int, dst_h: int) -> bytearray:
    """Nearest-neighbor resampler for RGBA image buffers."""
    dst = bytearray(dst_w * dst_h * 4)
    x_ratio, y_ratio = float(src_w) / dst_w, float(src_h) / dst_h
    for y in range(dst_h):
        sy = min(int(y * y_ratio), src_h - 1)
        dst_row, src_row = y * dst_w * 4, sy * src_w * 4
        for x in range(dst_w):
            sx = min(int(x * x_ratio), src_w - 1)
            src_idx = src_row + sx * 4
            dst_idx = dst_row + x * 4
            dst[dst_idx : dst_idx + 4] = src_data[src_idx : src_idx + 4]
    return dst
