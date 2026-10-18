"""
Conversation history export engine.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import tarfile
import tempfile
from antigravity_suite.migration.constants import BOLD, MASTER_GEMINI, NC, REAL_HOME, log_info, log_success
from antigravity_suite.migration.import_history import trigger_history_merge
from antigravity_suite.migration.tar_utils import format_size, get_timestamp


def export_history(output_path: str | None = None) -> str:
    """Exports all conversation history, brain artifacts, summaries, and annotations."""
    if not output_path:
        output_path = os.path.join(REAL_HOME, f"antigravity-history-export-{get_timestamp()}.tar.gz")

    output_path = os.path.abspath(os.path.expanduser(output_path))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    log_info("Gathering conversation history for export...")
    trigger_history_merge()

    conv_dbs = glob.glob(os.path.join(MASTER_GEMINI, "conversations", "*.db"))
    brain_dirs = glob.glob(os.path.join(MASTER_GEMINI, "brain", "*"))
    log_info(f"Found {len(conv_dbs)} conversations and {len(brain_dirs)} brain artifact folders.")

    manifest = {
        "export_type": "history", "format_version": "1.0",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hostname": os.uname().nodename,
        "conversations_count": len(conv_dbs), "brain_folders_count": len(brain_dirs),
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        mf_p = os.path.join(tmpdir, "manifest.json")
        with open(mf_p, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        mode = "w:gz" if output_path.endswith(".gz") else "w"
        with tarfile.open(output_path, mode) as tar:
            tar.add(mf_p, arcname="manifest.json")
            for item in ["conversations", "brain", "annotations"]:
                p = os.path.join(MASTER_GEMINI, item)
                if os.path.isdir(p): tar.add(p, arcname=item, recursive=True)
            for sum_f in glob.glob(os.path.join(MASTER_GEMINI, "*summaries*")):
                if os.path.isfile(sum_f): tar.add(sum_f, arcname=os.path.basename(sum_f))

    log_success("History export package created successfully!")
    print(f"  • Destination Archive: {BOLD}{output_path}{NC} ({format_size(os.path.getsize(output_path))})")
    print(f"  • Total Conversations: {len(conv_dbs)}\n  • Total Brain Folders: {len(brain_dirs)}")
    return output_path
