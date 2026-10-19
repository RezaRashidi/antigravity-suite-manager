# Issue 18: Watcher Daemon Self-Trigger Loop (app_storage.json & WAL) and Physical DB Deletion Guard

### Symptoms
* Background service `antigravity-sync.service` consumed 50%–99% CPU continuously, triggering full history merges every 30 seconds.
* Active conversations unexpectedly disappeared from the sidebar and were purged into `~/.config/antigravity/backups/trash/`.
* When clicking on restored conversations, the app showed empty conversation states or infinite loading spinners because the physical database had been trashed.

### Root Cause Analysis & Forensics

1. **Inotify Event Poisoning on Electron UI State (`app_storage.json`)**:
   In `src/antigravity_suite/history/watcher_debounce.py` and `watcher_targets.py`:
   ```python
   # Obsolete filter included app_storage.json and WAL
   return (
       base.endswith(".db")
       or base.endswith(".jsonl")
       or base.endswith(".md")
       or base.endswith(".vscdb")
       or base.endswith(".vscdb-wal")
       or base == "app_storage.json"
   )
   ```
   * Electron writes to `~/.config/Antigravity/storage/app_storage.json` on window focus/blur, window resize, scroll position updates, and periodic internal timers every 10–30 seconds.
   * `app_storage.json` is not a conversation file, but its modification triggered the watcher debounce tracker.

2. **Self-Trigger Feedback Loop via SQLite WAL**:
   Whenever `merge_histories()` wrote unified state to `state.vscdb`, SQLite committed transactions via Write-Ahead Logging (`state.vscdb-wal`).
   Because `base.endswith(".vscdb-wal")` was treated as a relevant event, the merge triggered an inotify event on its own write operations, re-triggering the daemon continuously.

3. **Asymmetric Deletion Logic Purging Active Chats (`del_ide`)**:
   In `src/antigravity_suite/history/deletion_sync.py`:
   ```python
   # Obsolete logic:
   del_ide = set() if (...) else ((prev_ide - cur_ide) - tombstones)
   to_purge = del_app | del_ide | ghost_ids
   ```
   * In Antigravity IDE, `state.vscdb` often only exposes conversations belonging to the *currently opened workspace folder*.
   * If a user switched workspaces, conversations outside that workspace were missing from `cur_ide`.
   * The deletion synchronization code misinterpreted this workspace scoping as user-initiated deletion and aggressively purged valid conversations (moving `.db`, `.pbtxt`, and `brain/` to trash and recording tombstones).
   * Over 12 large, active conversations (such as `ff12677b` with 709 steps and `7b382c83` with 3684 steps) were accidentally trashed during background cycles.

### Solutions Applied

1. **Excluding UI State & SQLite Temporary Files from Watcher**:
   Updated `src/antigravity_suite/history/watcher_debounce.py`:
   ```python
   def is_relevant_event(ev_path: str) -> bool:
       base = os.path.basename(ev_path)
       if (
           not base
           or base.startswith("conversation_summaries")
           or base.endswith(".pbtxt")
           or base.endswith(".pb")
           or base.endswith("-wal")
           or base.endswith("-shm")
           or base == "transcript_full.jsonl"
           or base == "app_storage.json"
       ):
           return False
       return (
           base.endswith(".db")
           or base.endswith(".jsonl")
           or base.endswith(".md")
           or base.endswith(".vscdb")
       )
   ```
   In `src/antigravity_suite/history/watcher_targets.py`, removed `app_storage.json` from `extra_files` registration so inotify watches are never placed on Electron UI state.

2. **Physical Database Existence Guard in Deletion Sync**:
   In `src/antigravity_suite/history/deletion_sync.py`, added a hard safeguard preventing any conversation from being marked for deletion if its physical SQLite database exists on disk and is non-empty:
   ```python
   all_conv = [effective_master / "conversations"] + [Path(p) for p in conv_pools]
   del_ide = {
       c for c in del_ide
       if not any((d / f"{c}.db").is_file() and (d / f"{c}.db").stat().st_size > 100 for d in all_conv)
   }
   ```

3. **Complete Restoration of Trashed & Missing Conversations**:
   * Recovered all 15 active conversations from `/home/reza/.config/antigravity/backups/trash/` and historical pools.
   * Restored both SQLite databases and brain logs (`transcript.jsonl`, `transcript_full.jsonl`).
   * Removed all 15 UUIDs from `sync_manifest.json["tombstones"]` across all profile roots.

### Verification
* Monitored `antigravity-sync.service` (`systemctl --user status antigravity-sync.service`):
  * Process state: `STAT Ss` (sleeping on `epoll.poll(timeout=2.0)` at 0.0% CPU).
  * Only wakes up when an authentic conversation event occurs (such as new prompts in `transcript.jsonl` or `.db` commits).
* Verified `del_ide` never marks existing conversations for deletion.
* All 304 conversations verified present in `state.vscdb` and `agyhub_summaries_proto.pb`.
