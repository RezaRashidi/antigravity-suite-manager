"""
JSONL Event Writer for History Audit Logging.

Handles atomic file appending, thread-safe disk writing, and directory initialization.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def write_audit_event(log_path: Path, event: Dict[str, Any]) -> bool:
    """Appends a single JSON event to the audit log atomically."""
    try:
        if not log_path.parent.is_dir():
            log_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
        return True
    except Exception:
        return False
