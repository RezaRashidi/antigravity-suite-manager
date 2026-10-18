"""
Step 132 (Tool Execution) Metadata and Payload Builders.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from antigravity_suite.proto.wire import encode_tag_bytes, encode_tag_uint


def build_step132_payload(
    base_meta: bytearray,
    status: int,
    content: Any,
    typ: str,
    out_idx: int,
    pending_tool_calls: List[Dict[str, Any]],
) -> Tuple[bytes, bytes]:
    """Builds Step 132 (Tool Execution) metadata and payload."""
    meta = bytearray(base_meta)
    tc = pending_tool_calls.pop(0) if pending_tool_calls else {}
    tc_id, tc_name = tc.get("id") or f"call_{out_idx}", tc.get("name") or typ.lower()
    tc_args = tc.get("args", {})
    if isinstance(tc_args, str):
        try:
            tc_args = json.loads(tc_args)
        except Exception:
            tc_args = {}

    tc_b = bytearray()
    tc_b += encode_tag_bytes(1, str(tc_id).encode("utf-8", errors="ignore"))
    tc_b += encode_tag_bytes(2, str(tc_name).encode("utf-8", errors="ignore"))
    tc_b += encode_tag_bytes(3, json.dumps(tc_args).encode("utf-8", errors="ignore"))
    tc_b += encode_tag_bytes(9, str(tc_name).encode("utf-8", errors="ignore"))
    meta += encode_tag_bytes(4, bytes(tc_b))

    payload = bytearray()
    payload += encode_tag_uint(1, 132)
    payload += encode_tag_uint(4, status)
    payload += encode_tag_bytes(5, bytes(meta))

    t_bytes = bytearray()
    if isinstance(tc_args, dict):
        for k, v in tc_args.items():
            pair = bytearray()
            pair += encode_tag_bytes(1, str(k).encode("utf-8", errors="ignore"))
            pair += encode_tag_bytes(2, (json.dumps(v) if isinstance(v, (dict, list)) else str(v)).encode("utf-8", errors="ignore"))
            t_bytes += encode_tag_bytes(1, bytes(pair))
    if content:
        out_sub = bytearray()
        out_sub += encode_tag_bytes(1, str(content).encode("utf-8", errors="ignore"))
        t_bytes += encode_tag_bytes(2, bytes(out_sub))
    payload += encode_tag_bytes(140, bytes(t_bytes))
    return bytes(meta), bytes(payload)
