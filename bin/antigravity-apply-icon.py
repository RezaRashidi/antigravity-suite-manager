#!/usr/bin/env python3
"""
Antigravity Runtime Window & Tray Synchronizer CLI Entry Point.
# Reference: [16, 24, 32, 48, 64, 128]
# Reference: getattr(apply_icon_to_windows, "_patched_wids", set())
"""

from __future__ import annotations

import os
import sys
import time
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

from antigravity_suite.icon import *

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--focus":
        acc = sys.argv[2] if len(sys.argv) > 2 else "2"
        focus_window(acc)
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        for _ in range(30):
            time.sleep(1)
            apply_icon_to_windows()
    else:
        apply_icon_to_windows()
