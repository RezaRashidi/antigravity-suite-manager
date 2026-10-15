"""
Antigravity Conversation History, Summaries, and Synchronization Package.
"""

from antigravity.history.discovery import discover_all_history_sources
from antigravity.history.extractor import (
    extract_conv_text,
    get_annotation_title,
    sync_annotation_file,
)
from antigravity.history.merger import merge_histories
from antigravity.history.models import ConversationSummary, SyncStats
from antigravity.history.sqlite_store import (
    ensure_summaries_schema,
    get_actual_steps_count,
    load_existing_summaries,
    upsert_summary,
)
from antigravity.history.synthesizer import (
    is_synthesized_db_incomplete,
    parse_step14_user_prompt,
    synthesize_db_from_transcript,
)
from antigravity.history.watcher import watch_mode

__all__ = [
    "ConversationSummary",
    "SyncStats",
    "discover_all_history_sources",
    "extract_conv_text",
    "get_annotation_title",
    "sync_annotation_file",
    "ensure_summaries_schema",
    "load_existing_summaries",
    "upsert_summary",
    "get_actual_steps_count",
    "is_synthesized_db_incomplete",
    "parse_step14_user_prompt",
    "synthesize_db_from_transcript",
    "merge_histories",
    "watch_mode",
]
