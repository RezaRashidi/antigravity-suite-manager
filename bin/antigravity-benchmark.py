#!/usr/bin/env python3
"""
Antigravity AI Response Speed & Latency Benchmark CLI runner.
"""

from __future__ import annotations

import os
import sys

_SRC_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "src"))
if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from antigravity_suite.benchmark.cli import main

if __name__ == "__main__":
    sys.exit(main())
