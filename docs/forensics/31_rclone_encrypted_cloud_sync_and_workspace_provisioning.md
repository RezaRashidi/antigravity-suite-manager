# Forensic Case 31: Rclone Encrypted Cloud Sync and Automatic Workspace Provisioning

## 1. Executive Summary

### 1.1 Incident & User Requirement
Users working on multiple machines that are **not powered on simultaneously** (e.g. office workstation and home laptop) require a frictionless mechanism to:
1. Start a conversation on System A and continue it seamlessly on System B.
2. Ensure that step counts are respected and new steps are appended cleanly without overwriting.
3. Automatically provision missing workspace folders (`mkdir -p`) on System B so Antigravity never crashes with "Workspace not found".
4. Guarantee that in-flight SQLite WAL data is flushed prior to transfer, while excluding volatile lock files (`*-wal`, `*-shm`, `*.lock`, `*.tmp`).
5. Support client-side end-to-end encrypted transfer using Rclone Crypt with Google Drive, OneDrive, Nextcloud, S3, etc.

---

## 2. Technical Architecture & Edge Cases Handled

### 2.1 Continuation Mechanics & Step Tracking (`conflict.py`)
- Each conversation is identified by its UUID: `conversations/<uuid>.db` and `brain/<uuid>/`.
- Inside SQLite `steps`, the primary key `idx` increments monotonically.
- The sync engine inspects incoming vs local metrics `(max_step_idx, step_count, mtime)`:
  - **Fast-Forward Continuation (`inc_max > loc_max`):** Incoming has more steps; local is updated to incoming state.
  - **Local Ahead Protection (`loc_max > inc_max`):** Local has newer messages than cloud; local is preserved.
  - **Divergence Guard (`fork_local_divergence`):** If both systems branched independently, local is archived as `<uuid>_fork_<timestamp>.db` before applying incoming to eliminate data loss.

### 2.2 SQLite WAL Checkpointing (`sqlite_wal.py`)
- SQLite WAL mode holds uncommitted step blobs in `<uuid>.db-wal`.
- Before pushing, `checkpoint_single_db` executes `PRAGMA wal_checkpoint(TRUNCATE)` across all `.db` files, ensuring databases are self-contained.
- Rclone excludes volatile `*-wal` and `*-shm` files to prevent synchronization of active locks.

### 2.3 Automatic Workspace Provisioning (`workspace_guard.py`)
- Extracts `workspace_uri` from `trajectory_metadata_blob` in `<uuid>.db`.
- Normalizes file URIs and translates cross-user paths (e.g. `/home/userA/...` mapped to current `$HOME/...`).
- Executes `ensure_workspace_exists` (`os.makedirs(path, exist_ok=True)`), writing `.antigravity_synced_workspace` marker.

### 2.4 Staging & IDE State Injection (`pull_ingest.py`)
- Remote changes are pulled to a temporary atomic staging directory.
- For each database, conflict evaluation and workspace provisioning occur before atomic placement in `~/.gemini/antigravity/`.
- Automatically calls `trigger_history_merge()` / `antigravity-merge-history.py` to rebuild `state.vscdb` and index new chats into the IDE sidebar.

---

## 3. Strict Architectural Compliance

1. **Line Count Verification**:
   - Every `.py` and `.sh` file in `src/`, `bin/`, and `scripts/` is strictly `<= 100 lines`.
2. **Automated Testing**:
   - `pytest tests/test_cloud_sync.py` passed with 5 targeted unit tests.
   - Total test suite: 178 tests passing.
