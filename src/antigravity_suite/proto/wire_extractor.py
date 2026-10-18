"""
Protobuf Binary Trajectory and Entry Extractor.
"""

from __future__ import annotations

import base64
import re
from typing import Dict

from antigravity_suite.proto.wire_pure import extract_pure_binary_summary
from antigravity_suite.proto.wire_varint import read_varint


def extract_entries_from_proto(data: bytes) -> Dict[str, bytes]:
    """Extracts {uuid: pure_binary_summary_bytes} from binary summaries proto."""
    entries: Dict[str, bytes] = {}
    if not data:
        return entries
    pos, total = 0, len(data)

    while pos < total:
        tag_wire, pos = read_varint(data, pos)
        wire_type, tag_num = tag_wire & 7, tag_wire >> 3

        if wire_type == 0:
            _, pos = read_varint(data, pos)
        elif wire_type == 1:
            pos += 8
        elif wire_type == 5:
            pos += 4
        elif wire_type != 2:
            break
        else:
            length, pos = read_varint(data, pos)
            if pos + length > total:
                break
            entry_data = data[pos : pos + length]
            pos += length
            _dispatch_proto_entry(tag_num, entry_data, entries)

    return entries


def _dispatch_proto_entry(tag_num: int, entry_data: bytes, entries: Dict[str, bytes]) -> None:
    if tag_num == 3 and re.match(rb"^[A-Za-z0-9+/=\s]+$", entry_data):
        try:
            sub = extract_entries_from_proto(base64.b64decode(entry_data))
            if sub:
                entries.update(sub)
        except Exception:
            pass
    elif tag_num == 1:
        _parse_map_entry(entry_data, entries)


def _parse_map_entry(entry_data: bytes, entries: Dict[str, bytes]) -> None:
    epos, elen = 0, len(entry_data)
    entry_key, entry_val = None, None
    while epos < elen:
        try:
            etag_wire, epos = read_varint(entry_data, epos)
            ewire, etag = etag_wire & 7, etag_wire >> 3
            if ewire == 0:
                _, epos = read_varint(entry_data, epos)
            elif ewire == 1:
                epos += 8
            elif ewire == 5:
                epos += 4
            elif ewire == 2:
                flen, epos = read_varint(entry_data, epos)
                if epos + flen > elen:
                    break
                fbytes = entry_data[epos : epos + flen]
                epos += flen
                if etag == 1:
                    entry_key = fbytes.decode("ascii", "ignore")
                elif etag in (2, 3):
                    entry_val = fbytes
            else:
                break
        except Exception:
            break

    if entry_key and entry_val:
        if entry_key == "trajectorySummaries":
            sub = extract_entries_from_proto(entry_val)
            if sub:
                entries.update(sub)
        else:
            pure = extract_pure_binary_summary(entry_val)
            if pure:
                entries[entry_key] = pure
    else:
        sub = extract_entries_from_proto(entry_data)
        if sub:
            entries.update(sub)
