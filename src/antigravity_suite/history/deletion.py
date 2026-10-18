"""
Bi-directional Conversation Deletion and Tombstone Synchronization Facade.
"""

from __future__ import annotations

from antigravity_suite.history.deletion_manifest import (
    MANIFEST_FILENAME,
    get_manifest_path,
    get_tombstones,
    load_manifest,
    save_manifest,
)
from antigravity_suite.history.deletion_purge import purge_conversation
from antigravity_suite.history.deletion_rpc import (
    find_running_language_servers,
    notify_language_servers_deletion,
)
from antigravity_suite.history.deletion_storage import purge_conversation_from_app_storage
from antigravity_suite.history.deletion_sync import detect_and_sync_deletions
from antigravity_suite.history.deletion_trash import (
    archive_deleted_conversation,
    restore_chat_from_trash,
)
from antigravity_suite.history.deletion_vscdb import (
    get_active_ide_ids,
    purge_conversation_from_vscdb,
)

__all__ = [
    "MANIFEST_FILENAME",
    "get_manifest_path",
    "load_manifest",
    "save_manifest",
    "get_tombstones",
    "find_running_language_servers",
    "notify_language_servers_deletion",
    "get_active_ide_ids",
    "purge_conversation_from_vscdb",
    "purge_conversation_from_app_storage",
    "archive_deleted_conversation",
    "restore_chat_from_trash",
    "purge_conversation",
    "detect_and_sync_deletions",
]
