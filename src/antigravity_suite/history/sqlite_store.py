"""
SQLite Storage Adapter Facade for conversation_summaries.db.
"""

from __future__ import annotations

from antigravity_suite.history.sqlite_fts import (
    repair_fts_zero_timestamps,
    sync_conversations_fts,
)
from antigravity_suite.history.sqlite_ops import (
    upsert_summary,
)
from antigravity_suite.history.sqlite_schema import (
    copy_sqlite_db_safely,
    ensure_summaries_schema,
)
from antigravity_suite.history.sqlite_steps import (
    _STEP_COUNT_CACHE,
    clear_step_count_cache,
    get_actual_steps_count,
    load_existing_summaries,
)

__all__ = [
    "_STEP_COUNT_CACHE",
    "ensure_summaries_schema",
    "copy_sqlite_db_safely",
    "load_existing_summaries",
    "sync_conversations_fts",
    "upsert_summary",
    "repair_fts_zero_timestamps",
    "clear_step_count_cache",
    "get_actual_steps_count",
]
