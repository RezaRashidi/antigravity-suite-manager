#!/usr/bin/env python3
"""
Antigravity History Synchronization CLI Entry Point.

Thin, modular CLI wrapper maintaining full backward-compatibility while
delegating core logic to the modular `antigravity_suite` package.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add package source directories to sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_USER_HOME = Path(os.environ.get("REAL_HOME", os.path.expanduser("~"))).resolve()

_CANDIDATES = [
    os.environ.get("ANTIGRAVITY_SUITE_DIR") and Path(os.environ["ANTIGRAVITY_SUITE_DIR"]) / "src",
    _CURRENT_DIR.parent / "src",
    _USER_HOME / ".antigravity-suite-manager" / "src",
    _USER_HOME / "PhpstormProjects" / "antigravity-suite-manager" / "src",
    Path.cwd() / "src",
]

for _cand in _CANDIDATES:
    if _cand and isinstance(_cand, Path) and _cand.is_dir() and str(_cand) not in sys.path:
        sys.path.insert(0, str(_cand))

# Re-export all public API symbols for complete backwards compatibility
from antigravity_suite.auth import refresh_ide_oauth_token
from antigravity_suite.cli.merge import build_parser, main, print_report
from antigravity_suite.config import DEFAULT_CONFIG, SuiteConfig, get_user_home
from antigravity_suite.history import (
    ConversationSummary,
    SyncStats,
    discover_all_history_sources,
    ensure_summaries_schema,
    extract_conv_text,
    get_annotation_title,
    is_synthesized_db_incomplete,
    load_existing_summaries,
    merge_histories,
    parse_step14_user_prompt,
    sync_annotation_file,
    synthesize_db_from_transcript,
    upsert_summary,
    watch_mode,
)
from antigravity_suite.proto import (
    build_cascade_summary,
    build_summaries_state,
    build_trajectory_metadata_blob,
    build_unified_state_sync,
    encode_annotations_field,
    encode_tag_bytes,
    encode_tag_uint,
    encode_timestamp_field,
    encode_varint,
    extract_entries_from_proto,
    extract_pure_binary_summary,
    get_last_user_step_index,
    parse_cascade_summary,
    parse_trajectory_metadata_blob,
    read_varint,
)

__all__ = [
    "encode_varint",
    "read_varint",
    "encode_tag_bytes",
    "encode_tag_uint",
    "encode_timestamp_field",
    "encode_annotations_field",
    "get_last_user_step_index",
    "build_cascade_summary",
    "parse_cascade_summary",
    "extract_pure_binary_summary",
    "extract_entries_from_proto",
    "get_annotation_title",
    "refresh_ide_oauth_token",
    "parse_step14_user_prompt",
    "is_synthesized_db_incomplete",
    "build_trajectory_metadata_blob",
    "parse_trajectory_metadata_blob",
    "sync_annotation_file",
    "synthesize_db_from_transcript",
    "extract_conv_text",
    "build_summaries_state",
    "build_unified_state_sync",
    "discover_all_history_sources",
    "merge_histories",
    "watch_mode",
    "main",
    "build_parser",
    "print_report",
]

if __name__ == "__main__":
    sys.exit(main())
