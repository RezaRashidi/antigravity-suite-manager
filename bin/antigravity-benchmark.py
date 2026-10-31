#!/usr/bin/env python3
"""
Antigravity AI Response Speed & Latency Benchmark CLI runner.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_cur = Path(__file__).resolve().parent
_real_home = os.environ.get("REAL_HOME") or str(Path.home())
_candidates = [
    os.environ.get("ANTIGRAVITY_SUITE_DIR") and Path(os.environ["ANTIGRAVITY_SUITE_DIR"]) / "src",
    _cur.parent / "src",
    Path(_real_home) / ".antigravity-suite-manager" / "src",
    Path.home() / ".antigravity-suite-manager" / "src",
    Path("/opt/antigravity-suite-manager/src"),
    Path.cwd() / "src",
]
for _c in _candidates:
    if _c and Path(_c).is_dir():
        _c_str = str(_c)
        if _c_str not in sys.path:
            sys.path.insert(0, _c_str)
        break

from antigravity_suite.benchmark.cli import main

if __name__ == "__main__":
    sys.exit(main())
