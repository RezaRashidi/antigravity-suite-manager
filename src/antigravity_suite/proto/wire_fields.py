"""
Protobuf Field Encoders for Timestamps and Annotations.
"""

from __future__ import annotations

import datetime
import re
import time
from typing import Optional, Union

from antigravity_suite.proto.wire_varint import encode_tag_uint


def encode_timestamp_field(
    dt_val: Optional[Union[str, int, float, datetime.datetime]] = None,
    nanos: int = 0,
) -> bytes:
    """Encodes an ISO timestamp string or numeric timestamp into google.protobuf.Timestamp."""
    secs, calculated_nanos = 0, nanos
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
                clean = re.sub(r"(\.\d{6})\d+", r"\1", s_str.replace("Z", "+00:00"))
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
    """Encodes submessage Field 16 (annotations / read-state) for CascadeTrajectorySummary."""
    sub = bytearray()
    if last_user_step < 0 and step_count > 0:
        last_user_step = max(0, step_count - 1)
    if last_user_step >= 0:
        sub += encode_tag_uint(4, last_user_step)
    if step_count > 0:
        sub += encode_tag_uint(5, step_count)
    return bytes(sub)
