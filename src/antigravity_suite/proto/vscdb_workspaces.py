"""
Protobuf Encoder and Parser for VS Code sidebarWorkspaces State.
"""

from __future__ import annotations

import base64
from typing import Dict, List, Optional, Tuple

from antigravity_suite.proto.wire import (
    encode_tag_bytes,
    encode_tag_uint,
    read_varint,
)


def build_sidebar_workspace_bytes(ws_uri: str, order: int = -1) -> bytes:
    """Constructs a SidebarWorkspace protobuf binary payload for a workspace URI."""
    disp = bytearray()
    disp += encode_tag_uint(2, 1)  # only_show_first_few_convos = True
    disp += encode_tag_uint(3, order if order >= 0 else 0xFFFFFFFFFFFFFFFF)
    sw = bytearray()
    sw += encode_tag_bytes(4, ws_uri.encode("utf-8"))
    sw += encode_tag_bytes(5, bytes(disp))
    return bytes(sw)


def parse_sidebar_workspaces(val_b64: Optional[str]) -> Dict[str, bytes]:
    """Parses existing sidebarWorkspaces Topic from base64 string."""
    workspaces: Dict[str, bytes] = {}
    if not val_b64:
        return workspaces
    try:
        raw = base64.b64decode(val_b64)
    except Exception:
        return workspaces
    pos, total = 0, len(raw)
    while pos < total:
        try:
            tw, pos = read_varint(raw, pos)
            wt = tw & 7
            if wt == 2:
                l, pos = read_varint(raw, pos)
                entry_raw = raw[pos : pos + l]
                pos += l
                k, v = _extract_workspace_entry(entry_raw)
                if k:
                    workspaces[k] = v or b""
            elif wt == 0:
                _, pos = read_varint(raw, pos)
            elif wt in (1, 5):
                pos += 8 if wt == 1 else 4
            else:
                break
        except Exception:
            break
    return workspaces


def _extract_workspace_entry(entry_raw: bytes) -> Tuple[Optional[str], Optional[bytes]]:
    epos, k, v = 0, None, None
    while epos < len(entry_raw):
        etw, epos = read_varint(entry_raw, epos)
        etag, ewt = etw >> 3, etw & 7
        if ewt == 2:
            el, epos = read_varint(entry_raw, epos)
            eval_ = entry_raw[epos : epos + el]
            epos += el
            if etag == 1:
                k = eval_.decode("utf-8", "ignore")
            elif etag == 2:
                v = eval_
        elif ewt == 0:
            _, epos = read_varint(entry_raw, epos)
        elif ewt in (1, 5):
            epos += 8 if ewt == 1 else 4
        else:
            break
    return k, v


def update_sidebar_workspaces_state(existing_b64: Optional[str], active_workspaces: List[str]) -> str:
    """Ensures all active workspace URIs are present in the sidebarWorkspaces Topic."""
    ws_dict = parse_sidebar_workspaces(existing_b64)
    for w in active_workspaces:
        if w and w not in ws_dict:
            inner = build_sidebar_workspace_bytes(w)
            inner_b64 = base64.b64encode(inner).decode("ascii")
            row = bytearray()
            row += encode_tag_bytes(1, inner_b64.encode("utf-8"))
            ws_dict[w] = bytes(row)

    entries = bytearray()
    for k, v in sorted(ws_dict.items()):
        entry = bytearray()
        entry += encode_tag_bytes(1, k.encode("utf-8"))
        entry += encode_tag_bytes(2, v)
        entries += encode_tag_bytes(1, bytes(entry))
    return base64.b64encode(bytes(entries)).decode("ascii")
