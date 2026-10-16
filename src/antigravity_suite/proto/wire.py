"""
Low-Level Protocol Buffers (Protobuf) Wire Format Encoders and Decoders.

Handles varint encoding/decoding, tagged length-delimited bytes, timestamps,
and binary entry parsing for Antigravity state files.
"""

from __future__ import annotations

import base64
import datetime
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union


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


def encode_timestamp_field(
    dt_val: Optional[Union[str, int, float, datetime.datetime]] = None,
    nanos: int = 0,
) -> bytes:
    """
    Encodes an ISO timestamp string or numeric timestamp into google.protobuf.Timestamp:
    Field 1: seconds (int64 varint)
    Field 2: nanos (int32 varint, optional)
    Guarantees timestamps are never <= 1000000000 (prevents year 1 or 1970).
    """
    secs = 0
    calculated_nanos = nanos
    if dt_val is not None:
        if isinstance(dt_val, (int, float)):
            secs = int(dt_val)
        elif isinstance(dt_val, datetime.datetime):
            if dt_val.tzinfo is None:
                dt_val = dt_val.replace(tzinfo=datetime.timezone.utc)
            secs = int(dt_val.timestamp())
            if not calculated_nanos and dt_val.microsecond:
                calculated_nanos = dt_val.microsecond * 1000
        else:
            try:
                s_str = str(dt_val).strip()
                clean = s_str.replace("Z", "+00:00")
                clean = re.sub(r"(\.\d{6})\d+", r"\1", clean)
                dt = datetime.datetime.fromisoformat(clean)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                secs = int(dt.timestamp())
                if not calculated_nanos and dt.microsecond:
                    calculated_nanos = dt.microsecond * 1000
            except Exception:
                secs = int(time.time())
    if secs <= 1000000000:
        secs = int(time.time())

    out = bytearray()
    out += encode_tag_uint(1, secs)
    if calculated_nanos > 0:
        out += encode_tag_uint(2, calculated_nanos)
    return bytes(out)


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


def _is_plausible_proto(b: bytes) -> bool:
    if not b or len(b) < 4:
        return False
    wire_type = b[0] & 7
    tag_num = b[0] >> 3
    return wire_type in (0, 2) and 1 <= tag_num <= 30


def extract_pure_binary_summary(raw: Any) -> Optional[bytes]:
    """
    Extracts raw protobuf binary summary from raw database value.
    Unwraps google.protobuf.Value string_value base64 string,
    Tag 1 (0x0A) or Tag 3 (0x1A) base64 wrappers, or direct ASCII base64 strings.
    """
    if not raw or not isinstance(raw, (bytes, bytearray)):
        return None

    raw_bytes = bytes(raw)

    # 1. Direct Base64 ASCII string check (e.g. starts with 'Cj' or is valid base64)
    if len(raw_bytes) >= 8 and re.match(rb"^[A-Za-z0-9+/=\s]+$", raw_bytes):
        try:
            decoded = base64.b64decode(raw_bytes)
            if _is_plausible_proto(decoded):
                return extract_pure_binary_summary(decoded)
        except Exception:
            pass

    # 2. Check if wrapped in Tag 1 (0x0A) or Tag 3 (0x1A) containing Base64 string
    if len(raw_bytes) >= 4 and raw_bytes[0] in (0x0A, 0x1A):
        pos = 1
        length, pos = read_varint(raw_bytes, pos)
        if pos + length == len(raw_bytes) and length >= 4:
            candidate_b64 = raw_bytes[pos : pos + length]
            if re.match(rb"^[A-Za-z0-9+/=\s]+$", candidate_b64):
                try:
                    decoded = base64.b64decode(candidate_b64)
                    if _is_plausible_proto(decoded):
                        return extract_pure_binary_summary(decoded)
                except Exception:
                    pass

    return raw_bytes


def extract_entries_from_proto(data: bytes) -> Dict[str, bytes]:
    """
    Extracts {uuid: pure_binary_summary_bytes} from binary summaries proto
    (e.g., agyhub_summaries_proto.pb or state.vscdb decoded base64).
    Recursively unwraps wrappers like google.protobuf.Value or outer messages.
    """
    entries: Dict[str, bytes] = {}
    if not data:
        return entries

    pos = 0
    total = len(data)

    while pos < total:
        tag_wire, pos = read_varint(data, pos)
        wire_type = tag_wire & 7
        tag_num = tag_wire >> 3

        if wire_type == 0:
            _, pos = read_varint(data, pos)
            continue
        elif wire_type == 1:
            pos += 8
            continue
        elif wire_type == 5:
            pos += 4
            continue
        elif wire_type != 2:
            break

        length, pos = read_varint(data, pos)
        if pos + length > total:
            break
        entry_data = data[pos : pos + length]
        pos += length

        # 1. Check if tag 3 contains a Base64 string (google.protobuf.Value wrapper)
        if tag_num == 3 and re.match(rb"^[A-Za-z0-9+/=\s]+$", entry_data):
            try:
                decoded = base64.b64decode(entry_data)
                sub_entries = extract_entries_from_proto(decoded)
                if sub_entries:
                    entries.update(sub_entries)
                    continue
            except Exception:
                pass

        # 2. Check if tag 1 is a map entry
        if tag_num == 1:
            epos = 0
            elen = len(entry_data)
            entry_key = None
            entry_val = None
            while epos < elen:
                try:
                    etag_wire, epos = read_varint(entry_data, epos)
                    ewire_type = etag_wire & 7
                    etag_num = etag_wire >> 3
                    if ewire_type == 0:
                        _, epos = read_varint(entry_data, epos)
                    elif ewire_type == 1:
                        epos += 8
                    elif ewire_type == 5:
                        epos += 4
                    elif ewire_type == 2:
                        flen, epos = read_varint(entry_data, epos)
                        if epos + flen > elen:
                            break
                        field_bytes = entry_data[epos : epos + flen]
                        epos += flen
                        if etag_num == 1:
                            entry_key = field_bytes.decode("ascii", "ignore")
                        elif etag_num in (2, 3):
                            entry_val = field_bytes
                    else:
                        break
                except Exception:
                    break

            if entry_key and entry_val:
                pure = extract_pure_binary_summary(entry_val)
                if pure:
                    entries[entry_key] = pure
            else:
                # Could be an outer container wrapping entries (e.g. in antigravityUnifiedStateSync)
                sub_entries = extract_entries_from_proto(entry_data)
                if sub_entries:
                    entries.update(sub_entries)

    return entries
