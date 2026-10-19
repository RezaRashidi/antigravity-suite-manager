#!/usr/bin/env python3
"""
Antigravity IDE Checksum Integrity Patcher CLI Entry Point.
"""

from __future__ import annotations

import argparse
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

from antigravity_suite.patch.ide_checksums import (
    find_ide_product_json,
    sync_ide_checksums,
    verify_ide_checksums,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity IDE Checksum Integrity Tool")
    parser.add_argument("ide_dir", nargs="?", default="/opt/antigravity", help="IDE root directory")
    parser.add_argument("--verify", action="store_true", help="Only verify checksums without updating")
    args = parser.parse_args()

    ide_dir = Path(args.ide_dir).resolve()
    if not find_ide_product_json(ide_dir):
        print(f"[ERROR] product.json not found in {ide_dir} or its resources/app.")
        sys.exit(1)

    if args.verify:
        results = verify_ide_checksums(ide_dir)
        mismatches = [k for k, v in results.items() if not v[2]]
        print(f"Verified {len(results)} files in {ide_dir}:")
        for k, (exp, act, match) in results.items():
            status = "OK" if match else "MISMATCH"
            print(f"  [{status}] {k}")
        if mismatches:
            print(f"[WARN] Found {len(mismatches)} mismatched checksum(s).")
            sys.exit(1)
        print("[SUCCESS] All checksums valid.")
        return

    updated, total = sync_ide_checksums(ide_dir)
    if updated > 0:
        print(f"[SUCCESS] Updated {updated}/{total} checksum(s) in product.json. Integrity intact.")
    else:
        print(f"[INFO] All {total} checksum(s) in product.json are already valid.")


if __name__ == "__main__":
    main()
