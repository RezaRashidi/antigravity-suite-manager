"""
Step 14 User Prompt Parser from Protobuf Payload.
"""

from __future__ import annotations

import re
from antigravity_suite.proto.wire import read_varint


def parse_step14_user_prompt(payload: bytes) -> str:
    """Extracts authentic user prompt text from Step 14 payload."""
    if not payload:
        return ""
    pos, p_len = 0, len(payload)
    clean_text, chunk_text = "", ""

    while pos < p_len:
        tag_wire, pos = read_varint(payload, pos)
        wire_type, tag_num = tag_wire & 7, tag_wire >> 3

        if wire_type == 2:
            length, pos = read_varint(payload, pos)
            val, pos = payload[pos : pos + length], pos + length
            if tag_num == 19:
                p19 = 0
                while p19 < len(val):
                    tw19, p19 = read_varint(val, p19)
                    w19, t19 = tw19 & 7, tw19 >> 3
                    if w19 == 2:
                        l19, p19 = read_varint(val, p19)
                        v19, p19 = val[p19 : p19 + l19], p19 + l19
                        if t19 == 2:
                            try:
                                clean_text = v19.decode("utf-8", errors="ignore")
                            except Exception:
                                pass
                        elif t19 == 3:
                            p_chunk = 0
                            while p_chunk < len(v19):
                                tw_c, p_chunk = read_varint(v19, p_chunk)
                                w_c = tw_c & 7
                                if w_c == 2:
                                    lc, p_chunk = read_varint(v19, p_chunk)
                                    vc, p_chunk = v19[p_chunk : p_chunk + lc], p_chunk + lc
                                    if (tw_c >> 3) == 1:
                                        try:
                                            chunk_text = vc.decode("utf-8", errors="ignore")
                                        except Exception:
                                            pass
                                elif w_c == 0:
                                    _, p_chunk = read_varint(v19, p_chunk)
                                elif w_c == 1:
                                    p_chunk += 8
                                elif w_c == 5:
                                    p_chunk += 4
                                else:
                                    break
                    elif w19 == 0:
                        _, p19 = read_varint(val, p19)
                    elif w19 == 1:
                        p19 += 8
                    elif w19 == 5:
                        p19 += 4
                    else:
                        break
        elif wire_type == 0:
            _, pos = read_varint(payload, pos)
        elif wire_type == 1:
            pos += 8
        elif wire_type == 5:
            pos += 4
        else:
            break

    raw_res = clean_text or chunk_text
    m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", raw_res, re.DOTALL)
    return m.group(1).strip() if m else raw_res.strip()
