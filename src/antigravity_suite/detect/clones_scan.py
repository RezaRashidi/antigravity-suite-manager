"""
Unified clone and account profile scanner.
"""

from __future__ import annotations

from typing import Any, Dict, List

from antigravity_suite.detect.clones_scan_app import scan_app_clones
from antigravity_suite.detect.clones_scan_ide import scan_ide_clones


def scan_clones(curr_app: str = "", curr_ide: str = "") -> List[Dict[str, Any]]:
    clones: List[Dict[str, Any]] = []
    clones.extend(scan_app_clones(curr_app=curr_app))
    clones.extend(scan_ide_clones(curr_ide=curr_ide))
    return clones


__all__ = ["scan_clones"]
