"""
Checkpoint Step (step_type = 23) Title Extraction.
"""

from __future__ import annotations

from typing import Optional

from antigravity_suite.history.extractor_cleaners import is_clean_title
from antigravity_suite.proto.wire import read_varint


def parse_step23_checkpoint_title(payload: bytes) -> Optional[str]:
    """Extracts authentic checkpoint title (Tag 30 -> Tag 4) from step_type = 23 binary payload."""
    if not payload:
        return None
    pos, data_len = 0, len(payload)
    while pos < data_len:
        tw, pos = read_varint(payload, pos)
        wt, tag = tw & 7, tw >> 3
        if wt == 2:
            l, pos = read_varint(payload, pos)
            val, pos = payload[pos : pos + l], pos + l
            if tag == 30:
                p30, val_len = 0, len(val)
                while p30 < val_len:
                    tw30, p30 = read_varint(val, p30)
                    wt30, tag30 = tw30 & 7, tw30 >> 3
                    if wt30 == 2:
                        l30, p30 = read_varint(val, p30)
                        v30, p30 = val[p30 : p30 + l30], p30 + l30
                        if tag30 == 4:
                            try:
                                cand = v30.decode("utf-8", errors="ignore").strip()
                                if cand and is_clean_title(cand):
                                    return cand
                            except Exception:
                                pass
                    elif wt30 == 0:
                        _, p30 = read_varint(val, p30)
                    elif wt30 == 1:
                        p30 += 8
                    elif wt30 == 5:
                        p30 += 4
                    else:
                        break
        elif wt == 0:
            _, pos = read_varint(payload, pos)
        elif wt == 1:
            pos += 8
        elif wt == 5:
            pos += 4
        else:
            break
    return None
