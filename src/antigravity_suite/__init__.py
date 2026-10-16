"""
Antigravity Suite Manager - Python Core Library.

Provides modular, robust tools for managing Google Antigravity and Antigravity IDE,
including cross-instance history synchronization, Protobuf wire serialization,
workspace binding, and credential lifecycle management.
"""

__version__ = "2.4.0"

from antigravity_suite.config import DEFAULT_CONFIG, SuiteConfig, get_user_home
from antigravity_suite.history.merger import merge_histories
from antigravity_suite.history.synthesizer import (
    is_synthesized_db_incomplete,
    synthesize_db_from_transcript,
)
from antigravity_suite.history.watcher import watch_mode
from antigravity_suite.proto.cascade import (
    build_cascade_summary,
    parse_cascade_summary,
)
from antigravity_suite.proto.trajectory import (
    build_trajectory_metadata_blob,
    parse_trajectory_metadata_blob,
)

__all__ = [
    "__version__",
    "SuiteConfig",
    "DEFAULT_CONFIG",
    "get_user_home",
    "merge_histories",
    "watch_mode",
    "build_cascade_summary",
    "parse_cascade_summary",
    "build_trajectory_metadata_blob",
    "parse_trajectory_metadata_blob",
    "is_synthesized_db_incomplete",
    "synthesize_db_from_transcript",
]
