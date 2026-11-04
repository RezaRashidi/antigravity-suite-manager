"""
Patcher utilities for Antigravity Suite (RTL, checksum integrity, and custom patches).
"""

from antigravity_suite.patch.ide_checksums import (
    compute_file_checksum,
    find_ide_product_json,
    sync_ide_checksums,
    verify_ide_checksums,
)

__all__ = [
    "compute_file_checksum",
    "find_ide_product_json",
    "sync_ide_checksums",
    "verify_ide_checksums",
]
