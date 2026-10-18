"""
Transcript Timestamp and Step Count Extraction.

Extracts authentic ISO timestamps and user interaction metrics from transcript.jsonl
using chunked reverse seeking for minimal memory overhead.
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path
from typing import Any, Optional, Tuple


def clean_iso_ts(ts_val: Any) -> Optional[str]:
    """Validates and formats an ISO timestamp string."""
    if not ts_val:
        return None
    try:
        s_str = str(ts_val).strip().replace("Z", "+00:00")
        clean = re.sub(r"(\.\d{6})\d+", r"\1", s_str)
        dt = datetime.datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        if dt.timestamp() <= 1000000000:
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
    except Exception:
        return None


def get_transcript_timestamps(transcript_path: Path) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extracts (created_time, last_user_input_time, last_modified_time) via streaming tail-seeking."""
    if not transcript_path.is_file() or transcript_path.stat().st_size == 0:
        return None, None, None
    try:
        fsize = transcript_path.stat().st_size
        created_time = None
        last_modified_time = None
        last_user_input_time = None

        with open(transcript_path, "rb") as f:
            first_line = f.readline().decode("utf-8", errors="ignore").strip()
            if first_line:
                try:
                    created_time = json.loads(first_line).get("created_at")
                except Exception:
                    pass

            chunk_size = min(fsize, 65536)
            f.seek(fsize - chunk_size)
            tail_lines = f.read(chunk_size).decode("utf-8", errors="ignore").splitlines()
            if fsize > chunk_size and tail_lines:
                tail_lines.pop(0)

            clean_lines = [line.strip() for line in tail_lines if line.strip()]
            if clean_lines:
                try:
                    last_modified_time = json.loads(clean_lines[-1]).get("created_at")
                except Exception:
                    pass
                for line in reversed(clean_lines):
                    try:
                        obj = json.loads(line)
                        if obj.get("type") == "USER_INPUT":
                            last_user_input_time = obj.get("created_at")
                            break
                    except Exception:
                        continue

            if not last_user_input_time and fsize > chunk_size:
                larger_chunk = min(fsize, 262144)
                f.seek(fsize - larger_chunk)
                t_lines = f.read(larger_chunk).decode("utf-8", errors="ignore").splitlines()
                if fsize > larger_chunk and t_lines:
                    t_lines.pop(0)
                for line in reversed(t_lines):
                    line_s = line.strip()
                    if line_s and "USER_INPUT" in line_s:
                        try:
                            obj = json.loads(line_s)
                            if obj.get("type") == "USER_INPUT":
                                last_user_input_time = obj.get("created_at")
                                break
                        except Exception:
                            continue

        return created_time, last_user_input_time, last_modified_time
    except Exception:
        return None, None, None
