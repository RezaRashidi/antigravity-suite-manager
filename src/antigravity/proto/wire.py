"""
Low-Level Protocol Buffers (Protobuf) Wire Format Encoders and Decoders.

Handles varint encoding/decoding, tagged length-delimited bytes, timestamps,
and binary entry parsing for Antigravity state files.
"""

from __future__ import annotations

import base64
import datetime
import re
from typing import Any, List, Optional, Tuple


def encode_varint(n: int) -> bytes:
    """Encodes an integer into standard Protobuf Varint wire format."""
    out = bytearray()
    val = n
    while val > 0x7F:
        out.append((val & 0x7F) | 0x80)
        val >>= 7
    out.append(val & 0x7F)
    return bytes(out)


def read_varint(b: bytes, pos: int) -> Tuple[int, int]:
    """Reads a Varint from buffer `b` starting at `pos`. Returns (value, next_pos)."""
    val = 0
    shift = 0
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
    tag_wire = (tag << 3) | 2
    return encode_varint(tag_wire) + encode_varint(len(b)) + b


def encode_tag_uint(tag: int, n: int) -> bytes:
    """Encodes a Varint field (Wire Type 0: tag << 3)."""
    tag_wire = tag << 3
    return encode_varint(tag_wire) + encode_varint(n)


def encode_timestamp_field(dt_str: str) -> bytes:
    """
    Encodes an ISO timestamp string into google.protobuf.Timestamp:
    Field 1: seconds (int64 varint)
    """
    try:
        clean = dt_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(clean)
        secs = int(dt.timestamp())
    except Exception:
        secs = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    return encode_tag_uint(1, secs)


def encode_annotations_field(step_count: int, last_user_step: int = -1) -> bytes:
    """
    Encodes submessage Field 16 (annotations / read-state) for CascadeTrajectorySummary.
    - Subtag 4: last_user_input_step_index (prevents unread 'New' badge in sidebar)
    - Subtag 5: total step_count
    """
    sub = bytearray()
    if last_user_step < 0 and step_count > 0:
        last_user_step = max(0, step_count - 1)
    if last_user_step >= 0:
        sub += encode_tag_uint(4, last_user_step)
    if step_count > 0:
        sub += encode_tag_uint(5, step_count)
    return bytes(sub)


def extract_pure_binary_summary(raw: Any) -> Optional[bytes]:
    """
    Extracts raw protobuf binary summary from raw database value.
    Unwraps google.protobuf.Value / ValueWrapper base64 string if present.
    """
    if not raw or not isinstance(raw, (bytes, bytearray)):
        return None

    # Check if raw is wrapped in ValueWrapper: tag 0x0a + varint len + base64 string
    if raw.startswith(b"\n"):
        pos = 1
        length, pos = read_varint(raw, pos)
        if pos + length == len(raw) and length >= 4:
            candidate_b64 = raw[pos : pos + length]
            if re.match(rb"^[A-Za-z0-9+/=]+$", candidate_b64):
                try:
                    decoded = base64.b64decode(candidate_b64, validate=True)
                    if decoded and len(decoded) >= 20:
                        return decoded
                except Exception:
                    pass
    return bytes(raw)


def extract_entries_from_proto(data: bytes) -> Dict[str, bytes]:
    """
    Extracts {uuid: pure_binary_summary_bytes} from binary summaries proto
    (e.g., agyhub_summaries_proto.pb or state.vscdb decoded base64).
    """
    entries: Dict[str, bytes] = {}
    pos = 0
    total = len(data)

    while pos < total:
        tag = data[pos]
        pos += 1
        length, pos = read_varint(data, pos)
        if pos + length > total:
            break
        entry_data = data[pos : pos + length]
        pos += length

        # In a map entry, tag 0x0a is key (uuid string, length 36 = 0x24)
        if tag == 0x0a and len(entry_data) > 38 and entry_data[0] == 0x0a and entry_data[1] == 0x24:
            uuid = entry_data[2:38].decode("ascii", "ignore")
            val_chunk = entry_data[38:]
            if len(val_chunk) > 2 and val_chunk[0] == 0x12:
                vlen, vpos = read_varint(val_chunk, 1)
                raw_val = val_chunk[vpos : vpos + vlen]
                pure = extract_pure_binary_summary(raw_val)
                if pure:
                    entries[uuid] = pure

    return entries
