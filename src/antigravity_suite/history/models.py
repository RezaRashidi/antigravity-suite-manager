"""
Data Models for Antigravity Conversation History, Summaries, and Sync Telemetry.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConversationSummary:
    """Represents a row in the conversation_summaries SQLite table."""

    conversation_id: str
    title: str = ""
    preview: str = ""
    step_count: int = 0
    last_modified_time: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
    )
    workspace_uris: str = ""
    status: str = "CASCADE_RUN_STATUS_IDLE"
    source: str = ""
    project_id: str = "outside-of-project"
    agent_name: str = "antigravity-agent"
    parent_conversation_id: str = ""
    nesting_depth: int = 0
    battle_id: str = ""
    winning_conversation_id: str = ""
    not_fully_idle: bool = False
    killed: bool = False
    last_user_input_time: str = ""
    last_user_input_step_index: int = -1
    app_data_dir: str = "antigravity"
    raw_summary: Optional[bytes] = None
    group_id: str = ""

    def __post_init__(self) -> None:
        if not self.last_user_input_time:
            self.last_user_input_time = self.last_modified_time


@dataclass
class SyncStats:
    """Telemetry report stats collected during a history synchronization pass."""

    conv_stores_scanned: int = 0
    brain_stores_scanned: int = 0
    db_files_merged: int = 0
    brain_folders_merged: int = 0
    databases_reconstructed: int = 0
    summaries_backfilled: int = 0
    conversations_updated: int = 0
    ide_state_ingested: int = 0
    total_active_history: int = 0

    def to_dict(self) -> dict:
        return {
            "conv_stores_scanned": self.conv_stores_scanned,
            "brain_stores_scanned": self.brain_stores_scanned,
            "db_files_merged": self.db_files_merged,
            "brain_folders_merged": self.brain_folders_merged,
            "databases_reconstructed": self.databases_reconstructed,
            "summaries_backfilled": self.summaries_backfilled,
            "conversations_updated": self.conversations_updated,
            "ide_state_ingested": self.ide_state_ingested,
            "total_active_history": self.total_active_history,
        }
