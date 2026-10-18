#!/usr/bin/env python3
"""
Antigravity History Synchronization CLI Entry Point.
"""

from __future__ import annotations

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

from antigravity_suite.auth import refresh_ide_oauth_token
from antigravity_suite.cli.merge import (
    build_parser,
    handle_list_backups,
    handle_restore_backup,
    main,
    print_report,
)
from antigravity_suite.config import DEFAULT_CONFIG, SuiteConfig, get_user_home
from antigravity_suite.history import *
from antigravity_suite.proto import *

__all__ = [
    "encode_varint", "read_varint", "encode_tag_bytes", "encode_tag_uint",
    "encode_timestamp_field", "encode_annotations_field", "get_last_user_step_index",
    "build_cascade_summary", "parse_cascade_summary", "extract_pure_binary_summary",
    "extract_entries_from_proto", "get_annotation_title", "refresh_ide_oauth_token",
    "parse_step14_user_prompt", "is_synthesized_db_incomplete", "build_trajectory_metadata_blob",
    "parse_trajectory_metadata_blob", "sync_annotation_file", "synthesize_db_from_transcript",
    "extract_conv_text", "build_summaries_state", "build_unified_state_sync",
    "discover_all_history_sources", "merge_histories", "watch_mode",
    "BackupEntry", "HistoryBackupManager", "handle_list_backups",
    "handle_restore_backup", "main", "build_parser", "print_report",
]

if __name__ == "__main__":
    sys.exit(main())
