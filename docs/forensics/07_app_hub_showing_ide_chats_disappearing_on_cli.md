# Issue 6: App (Hub) Showing IDE Chats & Disappearing on Click

### Symptoms
* Antigravity Desktop App (Hub) showed IDE workspace chats in its sidebar.
* Clicking on any IDE chat opened the conversation once, but immediately removed it from the sidebar history list upon loading.

### Diagnostic Methodology & Execution
* Analyzed Go Language Server startup flags and GORM SQLite queries:
  * Hub runs: `--app_data_dir=antigravity`
  * IDE runs: `--app_data_dir=antigravity-ide`
* In `merger.py`, the merger previously forced `app_data_dir = 'antigravity'` for all 308 chats and wrote all chats into `agyhub_summaries_proto.pb`.
* When Hub opened an IDE chat, Hub's Electron renderer inspected `workspace_uris` (`file://<workspace_path>`). Because Hub is a standalone launcher without an active IDE workspace, Hub dynamically filtered out the workspace conversation, purging it from view.
* In SQLite `conversation_summaries.db`, `upsert_summary()` lacked `app_data_dir` in `ON CONFLICT(conversation_id) DO UPDATE SET`, preventing partition migration.

### Solution Applied
* **Dual-Partition Isolation**:
  1. Updated `upsert_summary()` in [src/antigravity_suite/history/sqlite_store.py](src/antigravity_suite/history/sqlite_store.py) to update `app_data_dir` on conflict.
  2. Partitioned SQLite records: Conversations bound to an IDE workspace URI are marked `app_data_dir = 'antigravity-ide'` (257 chats). Standalone conversations are marked `app_data_dir = 'antigravity'` (53 chats).
  3. `serialize_master_proto()` now writes ONLY Hub-scoped chats (`app_data_dir == 'antigravity'`) into `agyhub_summaries_proto.pb`. Hub never loads IDE chats, completely eliminating ghost disappearing chats.
  4. IDE reads all workspace conversations via `state.vscdb` (`trajectorySummaries`, 309 chats).

---
