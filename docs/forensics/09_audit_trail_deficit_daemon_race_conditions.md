# Issue 8: Audit Trail Deficit & Daemon Race Conditions

### Symptoms
* `antigravity-sync.service` ran every 50 seconds in the background, making it impossible to determine what changed between runs.

### Solution Applied
* Created [src/antigravity_suite/history/audit.py](src/antigravity_suite/history/audit.py) logging structured JSONL events to `~/.gemini/antigravity/history_merger_audit.log`:
  * `TITLE_CHANGED`: Old title vs new title, reason.
  * `WORKSPACE_CHANGED`: Rebinding workspace URIs.
  * `PARTITION_CHANGED`: Partition transitions between `antigravity` and `antigravity-ide`.
  * `RUN_COMPLETE`: Detailed counts per run.

---
