"""
Antigravity Conversation History, Summaries, and Synchronization Package.
"""

from antigravity_suite.history.backup import BackupEntry, HistoryBackupManager
from antigravity_suite.history.discovery import discover_all_history_sources
from antigravity_suite.history.distribution import replicate_to_ide_profiles
from antigravity_suite.history.extractor import (
    extract_conv_text,
    get_annotation_info,
    get_annotation_title,
    sync_annotation_file,
)
from antigravity_suite.history.merger import merge_histories
from antigravity_suite.history.models import ConversationSummary, SyncStats
from antigravity_suite.history.pool_merger import merge_brain_folders, merge_raw_db_pools
from antigravity_suite.history.reconstruction import (
    gather_candidate_transcripts,
    reconstruct_missing_databases,
)
from antigravity_suite.history.sqlite_store import (
    ensure_summaries_schema,
    get_actual_steps_count,
    load_existing_summaries,
    upsert_summary,
)
from antigravity_suite.history.synthesizer import (
    is_synthesized_db_incomplete,
    parse_step14_user_prompt,
    synthesize_db_from_transcript,
)
from antigravity_suite.history.vscdb_sync import (
    discover_candidate_vscdbs,
    get_db_trajectory_meta,
    ingest_vscdb_summaries,
    write_vscdb_unified_state,
)
from antigravity_suite.history.watcher import watch_mode

__all__ = [
    "BackupEntry",
    "HistoryBackupManager",
    "ConversationSummary",
    "SyncStats",
    "discover_all_history_sources",
    "extract_conv_text",
    "get_annotation_info",
    "get_annotation_title",
    "sync_annotation_file",
    "ensure_summaries_schema",
    "load_existing_summaries",
    "upsert_summary",
    "get_actual_steps_count",
    "is_synthesized_db_incomplete",
    "parse_step14_user_prompt",
    "synthesize_db_from_transcript",
    "merge_raw_db_pools",
    "merge_brain_folders",
    "gather_candidate_transcripts",
    "reconstruct_missing_databases",
    "get_db_trajectory_meta",
    "discover_candidate_vscdbs",
    "ingest_vscdb_summaries",
    "write_vscdb_unified_state",
    "replicate_to_ide_profiles",
    "merge_histories",
    "watch_mode",
]
