#!/usr/bin/env python3
"""
Antigravity Cross-System Migration & Backup Tool CLI Entry Point.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_cur = Path(__file__).resolve().parent
_candidates = [
    os.environ.get("ANTIGRAVITY_SUITE_DIR") and Path(os.environ["ANTIGRAVITY_SUITE_DIR"]) / "src",
    _cur.parent / "src",
    Path.home() / ".antigravity-suite-manager" / "src",
    Path.home() / "PhpstormProjects" / "antigravity-suite-manager" / "src",
    Path.cwd() / "src",
]
for _c in _candidates:
    if _c and Path(_c).is_dir() and str(_c) not in sys.path:
        sys.path.insert(0, str(_c))

from antigravity_suite.migration import *
from antigravity_suite.migration.constants import *
from antigravity_suite.migration.import_history import trigger_history_merge
from antigravity_suite.migration.restore import restore_backup
from antigravity_suite.migration.safety import create_safety_backup

if __name__ == "__main__":
    sys.exit(main())
