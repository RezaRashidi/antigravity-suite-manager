# Master Relational Index (`conversation_summaries.db`)

The master SQLite database at `~/.gemini/antigravity/conversation_summaries.db` serves as the primary catalog indexed by the Language Server for both Desktop App and IDE.

### 4.1 Database Schema & Indices

```sql
CREATE TABLE `conversation_summaries` (
    `conversation_id`            TEXT PRIMARY KEY,
    `title`                      TEXT NOT NULL DEFAULT "",
    `preview`                    TEXT NOT NULL DEFAULT "",
    `step_count`                 INTEGER NOT NULL DEFAULT 0,
    `last_modified_time`         DATETIME NOT NULL,
    `workspace_uris`             TEXT NOT NULL DEFAULT "",               -- JSON array e.g. ["file:///path/to/project"]
    `status`                     TEXT NOT NULL DEFAULT "CASCADE_RUN_STATUS_IDLE",
    `source`                     TEXT NOT NULL DEFAULT "",
    `project_id`                 TEXT NOT NULL DEFAULT "outside-of-project", -- Project UUID or "outside-of-project"
    `agent_name`                 TEXT NOT NULL DEFAULT "antigravity-agent",
    `parent_conversation_id`     TEXT NOT NULL DEFAULT "",               -- Parent UUID if spawned by subagent
    `nesting_depth`              INTEGER NOT NULL DEFAULT 0,              -- Subagent recursion depth
    `battle_id`                  TEXT NOT NULL DEFAULT "",
    `winning_conversation_id`    TEXT NOT NULL DEFAULT "",
    `not_fully_idle`             NUMERIC NOT NULL DEFAULT 0,
    `killed`                     NUMERIC NOT NULL DEFAULT 0,
    `last_user_input_time`       DATETIME NOT NULL,
    `last_user_input_step_index` INTEGER NOT NULL DEFAULT -1,             -- Read/Unread flag (see Section 4.2)
    `app_data_dir`               TEXT NOT NULL DEFAULT "antigravity",     -- Instance partition key
    `raw_summary`                BLOB,                                    -- Complete CascadeTrajectorySummary protobuf
    `group_id`                   TEXT NOT NULL DEFAULT ""
);

CREATE INDEX `idx_conversation_summaries_last_user_input_time`
    ON `conversation_summaries` (`last_user_input_time`);
CREATE INDEX `idx_conversation_summaries_last_modified_time`
    ON `conversation_summaries` (`last_modified_time`);

-- Full-Text Search Virtual Table
CREATE VIRTUAL TABLE `conversations_fts` USING fts5(
    conversation_id UNINDEXED, chunk_index UNINDEXED, chunk_first_step UNINDEXED, chunk_last_step UNINDEXED,
    last_modified_time UNINDEXED, step_count UNINDEXED, last_step_created_at UNINDEXED, archived UNINDEXED,
    user_step_byte_offsets UNINDEXED, agent_step_byte_offsets UNINDEXED,
    title, workspace, project, user_body, agent_body,
    tokenize = 'unicode61 remove_diacritics 2', prefix = '1 2 3'
);
```

### 4.2 Unread / "New" ("تازه") Badge Mechanics
The UI sidebar marks a conversation as unread / "New" when:
1. `last_user_input_step_index == -1` while `step_count > 0`, OR
2. Protobuf Field 16 (`last_user_input_step_index`) in `CascadeTrajectorySummary` is omitted.

To mark a conversation as read and prevent spurious "New" badges, `last_user_input_step_index` must be set to the index of the last user step (`SELECT idx FROM steps WHERE step_type = 14 ORDER BY idx DESC LIMIT 1`).

---
