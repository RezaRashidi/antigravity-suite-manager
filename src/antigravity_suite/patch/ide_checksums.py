"""
Integrity checksum synchronizer for Antigravity IDE (VS Code OSS).
Prevents 'Your Antigravity IDE installation appears to be corrupt' notifications.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Tuple


def compute_file_checksum(filepath: Path | str) -> str:
    """Computes VS Code standard SHA-256 base64 checksum without '=' padding."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return base64.b64encode(h.digest()).decode("utf-8").rstrip("=")


def find_ide_product_json(ide_dir: Path | str) -> Optional[Path]:
    """Locates product.json within an IDE installation directory."""
    p = Path(ide_dir)
    for cand in [p / "resources" / "app" / "product.json", p / "product.json"]:
        if cand.is_file():
            return cand
    return None


def verify_ide_checksums(ide_dir: Path | str) -> Dict[str, Tuple[str, str, bool]]:
    """Verifies all checksums in product.json against live files on disk."""
    prod_path = find_ide_product_json(ide_dir)
    if not prod_path:
        return {}
    out_dir = prod_path.parent / "out"
    with open(prod_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    results = {}
    for rel_path, expected in data.get("checksums", {}).items():
        target = out_dir / rel_path
        if not target.is_file():
            results[rel_path] = (expected, "", False)
            continue
        actual = compute_file_checksum(target)
        results[rel_path] = (expected, actual, actual == expected)
    return results


def sync_ide_checksums(ide_dir: Path | str, dry_run: bool = False) -> Tuple[int, int]:
    """Updates product.json checksums to match patched bundle files on disk."""
    prod_path = find_ide_product_json(ide_dir)
    if not prod_path:
        return (0, 0)
    out_dir = prod_path.parent / "out"
    with open(prod_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    checksums = data.get("checksums", {})
    updated = 0
    for rel_path in list(checksums.keys()):
        target = out_dir / rel_path
        if not target.is_file():
            continue
        actual = compute_file_checksum(target)
        if checksums[rel_path] != actual:
            checksums[rel_path] = actual
            updated += 1
    if updated > 0 and not dry_run:
        with open(prod_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    return (updated, len(checksums))


def main() -> None:
    import sys
    ide_path = sys.argv[1] if len(sys.argv) > 1 else "/opt/antigravity"
    updated, total = sync_ide_checksums(ide_path)
    print(f"Checksums synchronized: {updated}/{total} updated for {ide_path}")


if __name__ == "__main__":
    main()
