# Forensic Analysis Case 50: Manual Chat Title Reversion via Stale VSCDB Overwrite and On-Demand Merger Mode Control

## Executive Summary
Following manual chat title renaming in the Antigravity Desktop App, renamed titles reverted to stale or default names within seconds to minutes (specifically reproduced on conversations `8561cc8a-2988-4371-9f9d-a2b27e622be1` and `5a9cebeb-9582-4fa9-97c0-4b5d2d885fb9`). 

Investigation revealed a dual regression:
1. `vscdb_ingest_update.py` ingested stale titles from VS Code IDE's `state.vscdb` into `conversation_summaries.db` without evaluating file timestamp freshness (`mtime`) against manual annotations (`annotations/<cid>.pbtxt`).
2. `checkpoint_sync.py` updated only the single highest step 23 checkpoint entry in conversation `.db` files, leaving older step 23 entries intact, which the Language Server re-broadcast upon session reload.

Additionally, to provide the operator with absolute control over synchronization timing, a dedicated merger mode controller (`manage-antigravity.sh merger [auto|manual|status|run]`) was implemented and wired across systemd services, app launchers, and the Control Center.

---

## Technical Root Cause Analysis

### 1. Stale Ingestion in `vscdb_ingest_update.py`
In commit `90c4188`, diff checking was introduced to detect title and preview changes between IDE `state.vscdb` and `conversation_summaries.db`:
```python
is_diff = (ide_sum.get("title") and ide_sum["title"] != existing_sum.get("title"))
if is_diff:
    cur.execute("UPDATE conversation_summaries SET title = ? ...", (ide_sum["title"], ...))
```
When a title was manually edited in the Desktop App:
- The Desktop App updated `annotations/<cid>.pbtxt` and `conversation_summaries.db`.
- The IDE's `state.vscdb` remained stale with the old title.
- During the next merger watch cycle, `vscdb_ingest_update` observed `ide_sum["title"] != existing_sum["title"]`, treated the stale IDE state as authoritative, and unconditionally reverted the title in `conversation_summaries.db`.

### 2. Multi-Checkpoint Step 23 Revival in Conversation Databases
A single conversation SQLite database can contain dozens of step 23 checkpoints (e.g. 29 checkpoints in `5a9cebeb-9582-4fa9-97c0-4b5d2d885fb9`).
`checkpoint_sync.py` previously executed:
```python
cur.execute(
    "SELECT step_index, payload FROM conversation_steps "
    "WHERE step_type = 23 ORDER BY step_index DESC LIMIT 1;"
)
```
Updating only the latest step 23 entry left preceding checkpoints with stale titles. When the Language Server traversed historical checkpoints during turn restoration, it parsed older step 23 payloads and revived the previous title.

---

## Architectural Remediation

### 1. Annotation Timestamp Priority (`vscdb_ingest_update.py` & `vscdb_ingest.py`)
- Evaluated `mtime` of `annotations/<cid>.pbtxt` against `vscdb_mtime`.
- If a manual annotation file exists and was modified *after* `state.vscdb`, any conflicting title from `state.vscdb` is discarded:
```python
if is_diff and vscdb_mtime is not None:
    ann_path = os.path.join(gemini_dir, "annotations", f"{conv_id}.pbtxt")
    if os.path.isfile(ann_path) and os.path.getmtime(ann_path) > vscdb_mtime:
        is_diff = False
```

### 2. Exhaustive Step 23 Checkpoint Updates (`checkpoint_sync.py`)
- Refactored `ensure_db_checkpoint_title` to fetch and update **all** `step_type = 23` rows in the conversation database:
```python
cur.execute("SELECT step_index, payload FROM conversation_steps WHERE step_type = 23;")
for row in cur.fetchall():
    # Update protobuf checkpoint title and commit back to database
```

### 3. On-Demand Merger Mode Controller (`merger_control.sh`)
Implemented `bin/lib/sh/merger_control.sh` (71 lines) and integrated CLI and Control Center actions:
- `manage-antigravity.sh merger status`: Displays whether merger is `AUTOMATIC (Active)` or `MANUAL (Disabled)`.
- `manage-antigravity.sh merger manual` / `disable`: Stops and disables `antigravity-sync.service` and writes `~/.config/antigravity/merger_disabled`.
- `manage-antigravity.sh merger auto` / `enable`: Removes marker file, enables and restarts `antigravity-sync.service`.
- `manage-antigravity.sh merger run` / `sync`: Executes one-shot manual synchronization.
- All App and IDE launchers check `~/.config/antigravity/merger_disabled` before launching one-shot merger subprocesses.

---

## Verification & Proof
- **Unit Tests**:
  - `test_ensure_db_checkpoint_title_updates_all_step23_entries`: Passed.
  - `test_update_existing_from_ide_respects_newer_annotation_mtime`: Passed.
  - Full suite: 247 passed in 8.85s.
- **Constraints**:
  - All modified `.py` and `.sh` files verified $\le 100$ lines.
