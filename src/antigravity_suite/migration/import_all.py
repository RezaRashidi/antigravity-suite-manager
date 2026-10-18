"""
Archive auto-detection and dispatch engine for import operations.
"""

from __future__ import annotations

import json
import os
import tarfile
import tempfile
from antigravity_suite.migration.constants import BOLD, NC, log_err, log_info
from antigravity_suite.migration.import_history import import_history
from antigravity_suite.migration.import_suite import import_suite
from antigravity_suite.migration.tar_utils import safe_extract_tar


def import_all(archive_path: str) -> bool:
    """Automatically detects archive type and performs required import(s)."""
    if not os.path.isfile(archive_path):
        log_err(f"Archive file not found: {archive_path}")
        return False

    manifest = None
    try:
        with tarfile.open(archive_path, "r:*") as tar:
            try:
                mf = tar.extractfile("manifest.json")
                if mf: manifest = json.load(mf)
            except KeyError: pass
    except Exception as e:
        log_err(f"Could not read archive: {e}")
        return False

    exp_type = manifest.get("export_type") if manifest else None
    if not exp_type:
        fn = os.path.basename(archive_path).lower()
        exp_type = "history" if "history" in fn else ("suite" if "suite" in fn else "all")

    log_info(f"Archive detected as type: {BOLD}{exp_type.upper()}{NC}")
    if exp_type == "history":
        return import_history(archive_path=archive_path)
    elif exp_type == "suite":
        return import_suite(archive_path=archive_path)
    elif exp_type in ["all", "full"]:
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(archive_path, "r:*") as tar:
                safe_extract_tar(tar, path=tmpdir)
            h_ok = import_history(extracted_dir=tmpdir)
            s_ok = import_suite(extracted_dir=tmpdir)
            return h_ok and s_ok
    else:
        log_err(f"Unknown archive export_type: {exp_type}")
        return False
