"""
Pure-Python PNG decoder and RGBA rasterizer without third-party dependencies.
"""

from __future__ import annotations

import os
import struct
import zlib
from typing import Optional, Tuple


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)


def reconstruct_png(png_path: str) -> Tuple[Optional[int], Optional[int], Optional[bytearray]]:
    """Decodes non-interlaced PNG into raw RGBA bytearray buffer."""
    if not os.path.exists(png_path): return None, None, None
    try:
        with open(png_path, "rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n": return None, None, None
            idat, plte, trns = bytearray(), bytearray(), bytearray()
            while True:
                chunk = f.read(8)
                if not chunk: break
                l, t = struct.unpack(">I4s", chunk)
                d = f.read(l); f.read(4)
                if t == b"IDAT": idat.extend(d)
                elif t == b"PLTE": plte.extend(d)
                elif t == b"tRNS": trns.extend(d)
                elif t == b"IEND": break

        with open(png_path, "rb") as f:
            f.seek(16)
            w, h, bit_d, col_t, _, _, interlace = struct.unpack(">IIBBBBB", f.read(13))
            if interlace != 0: return None, None, None

        raw = zlib.decompress(bytes(idat))
        ch = 4 if col_t == 6 else (3 if col_t == 2 else (2 if col_t == 4 else 1))
        bpp = ch * (2 if bit_d == 16 else 1)
        stride = 1 + w * bpp
        recon = bytearray(w * h * bpp)

        for y in range(h):
            filt_t = raw[y * stride]
            scan = raw[y * stride + 1 : (y + 1) * stride]
            row = bytearray(w * bpp)
            prev = recon[(y - 1) * w * bpp : y * w * bpp] if y > 0 else bytearray(w * bpp)
            for x in range(w * bpp):
                fx, ra = scan[x], (row[x - bpp] if x >= bpp else 0)
                rb, rc = prev[x], (prev[x - bpp] if x >= bpp else 0)
                if filt_t == 0: v = fx
                elif filt_t == 1: v = (fx + ra) & 0xff
                elif filt_t == 2: v = (fx + rb) & 0xff
                elif filt_t == 3: v = (fx + (ra + rb) // 2) & 0xff
                else: v = (fx + _paeth(ra, rb, rc)) & 0xff
                row[x] = v
            recon[y * w * bpp : (y + 1) * w * bpp] = row

        if bit_d == 16:
            recon = bytearray(recon[i * 2] for i in range(w * h * ch))

        rgba = bytearray(w * h * 4)
        if col_t == 6: rgba = recon
        elif col_t == 2:
            for i in range(w * h):
                rgba[i*4 : i*4+3] = recon[i*3 : i*3+3]
                rgba[i*4+3] = 255
        elif col_t == 4:
            for i in range(w * h):
                rgba[i*4 : i*4+3] = bytearray([recon[i*2]] * 3)
                rgba[i*4+3] = recon[i*2+1]
        elif col_t == 3:
            pl, tl = len(plte), len(trns)
            for i in range(w * h):
                idx = recon[i]
                if idx * 3 + 2 < pl: rgba[i*4 : i*4+3] = plte[idx*3 : idx*3+3]
                rgba[i*4+3] = trns[idx] if idx < tl else 255
        elif col_t == 0:
            for i in range(w * h):
                rgba[i*4 : i*4+3] = bytearray([recon[i]] * 3)
                rgba[i*4+3] = 255
        return w, h, rgba
    except Exception:
        return None, None, None
