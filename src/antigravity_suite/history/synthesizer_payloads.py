"""
Protobuf Step Payload Builders for User and Model Responses.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from antigravity_suite.history.synthesizer_tool_payloads import build_step132_payload
from antigravity_suite.proto.wire import encode_tag_bytes, encode_tag_uint

__all__ = [
    "build_step_meta",
    "build_step14_payload",
    "build_step15_payload",
    "build_step132_payload",
]


def build_step_meta(conv_id: str) -> bytearray:
    """Builds base metadata for a conversation step."""
    meta = bytearray()
    meta += encode_tag_bytes(12, conv_id.encode("utf-8"))
    sub = bytearray()
    sub += encode_tag_bytes(1, conv_id.encode("utf-8"))
    sub += encode_tag_bytes(4, conv_id.encode("utf-8"))
    meta += encode_tag_bytes(20, bytes(sub))
    return meta


def build_step14_payload(meta: bytearray, status: int, content: Any) -> bytes:
    """Builds Step 14 (User Request) payload."""
    payload = bytearray()
    payload += encode_tag_uint(1, 14)
    payload += encode_tag_uint(4, status)
    payload += encode_tag_bytes(5, bytes(meta))
    clean = content
    if isinstance(content, str):
        m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
        clean = m.group(1).strip() if m else content.strip()
    else:
        clean = str(content)
    u_bytes = bytearray()
    if clean:
        u_bytes += encode_tag_bytes(2, clean.encode("utf-8", errors="ignore"))
        chunk = bytearray()
        chunk += encode_tag_bytes(1, clean.encode("utf-8", errors="ignore"))
        u_bytes += encode_tag_bytes(3, bytes(chunk))
    payload += encode_tag_bytes(19, bytes(u_bytes))
    return bytes(payload)


def build_step15_payload(
    meta: bytearray, status: int, content: Any, thinking: Any,
    tool_calls: list, out_idx: int, pending_tool_calls: List[Dict[str, Any]],
) -> bytes:
    """Builds Step 15 (Model Response) payload."""
    payload = bytearray()
    payload += encode_tag_uint(1, 15)
    payload += encode_tag_uint(4, status)
    payload += encode_tag_bytes(5, bytes(meta))
    m_bytes = bytearray()
    if content:
        m_bytes += encode_tag_bytes(1, str(content).encode("utf-8", errors="ignore"))
    if thinking:
        m_bytes += encode_tag_bytes(3, str(thinking).encode("utf-8", errors="ignore"))
    m_bytes += encode_tag_bytes(6, b"antigravity-agent")
    if tool_calls:
        for tci, tc in enumerate(tool_calls):
            pending_tool_calls.append(tc)
            tc_b = bytearray()
            tc_id = tc.get("id") or f"call_{out_idx}_{tci}"
            tc_name = tc.get("name") or tc.get("function", {}).get("name", "")
            tc_args = tc.get("args") or tc.get("function", {}).get("arguments", "")
            tc_args_str = json.dumps(tc_args) if isinstance(tc_args, (dict, list)) else str(tc_args)
            if tc_id:
                tc_b += encode_tag_bytes(1, str(tc_id).encode("utf-8", errors="ignore"))
            if tc_name:
                tc_b += encode_tag_bytes(2, str(tc_name).encode("utf-8", errors="ignore"))
            if tc_args_str:
                tc_b += encode_tag_bytes(3, str(tc_args_str).encode("utf-8", errors="ignore"))
            if tc_name:
                tc_b += encode_tag_bytes(9, str(tc_name).encode("utf-8", errors="ignore"))
            m_bytes += encode_tag_bytes(7, bytes(tc_b))
    if content:
        m_bytes += encode_tag_bytes(8, str(content).encode("utf-8", errors="ignore"))
    m_bytes += encode_tag_uint(12, 2)
    payload += encode_tag_bytes(20, bytes(m_bytes))
    return bytes(payload)
