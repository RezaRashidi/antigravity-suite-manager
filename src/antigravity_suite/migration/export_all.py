"""
Unified export bundle generator combining History and Suite configurations.
"""

from __future__ import annotations

import datetime
import json
import os
import tarfile
import tempfile
from antigravity_suite.migration.constants import BOLD, NC, REAL_HOME, log_info, log_success
from antigravity_suite.migration.export_history import export_history
from antigravity_suite.migration.export_suite import export_suite
from antigravity_suite.migration.tar_utils import format_size, get_timestamp


def export_all(output_path: str | None = None) -> str:
    """Exports both History AND Suite configurations in a single unified archive."""
    if not output_path:
        output_path = os.path.join(REAL_HOME, f"antigravity-full-backup-{get_timestamp()}.tar.gz")

    output_path = os.path.abspath(os.path.expanduser(output_path))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    log_info("Creating full unified export package (History + Suite Configs)...")

    with tempfile.TemporaryDirectory() as tmpdir:
        hist_tar = os.path.join(tmpdir, "history_part.tar")
        suite_tar = os.path.join(tmpdir, "suite_part.tar")
        export_history(hist_tar)
        export_suite(suite_tar)

        manifest = {
            "export_type": "all", "format_version": "1.0",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "hostname": os.uname().nodename, "components": ["history", "suite"],
        }
        mf_p = os.path.join(tmpdir, "manifest.json")
        with open(mf_p, "w", encoding="utf-8") as f: json.dump(manifest, f, indent=2)

        with tarfile.open(output_path, "w:gz") as final_tar:
            final_tar.add(mf_p, arcname="manifest.json")
            added = {"manifest.json"}
            for sub_tar in [hist_tar, suite_tar]:
                with tarfile.open(sub_tar, "r:") as part:
                    for member in part.getmembers():
                        if member.name not in added:
                            f = part.extractfile(member) if member.isreg() else None
                            final_tar.addfile(member, f)
                            added.add(member.name)

    log_success(f"Full migration bundle created: {BOLD}{output_path}{NC} ({format_size(os.path.getsize(output_path))})")
    return output_path
