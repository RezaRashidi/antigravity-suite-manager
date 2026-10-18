# Issue 4: Metadata Inode Stagnation in Fast-Path Caching

### Symptoms
* Updates made to `transcript.jsonl` in pool profiles were silently ignored during merge sweeps.

### Diagnostic Methodology & Execution
* Inspected [src/antigravity_suite/history/pool_merger.py](src/antigravity_suite/history/pool_merger.py):
  ```python
  src_logs = os.path.join(b_item, ".system_generated", "logs")
  tgt_logs = target_brain_item / ".system_generated" / "logs"
  if tgt_logs.is_dir() and os.path.isdir(src_logs):
      if os.path.getmtime(src_logs) <= tgt_logs.stat().st_mtime:
          continue
  ```
* **Root Cause**: On POSIX filesystems, appending data to an existing file (`transcript.jsonl`) modifies only the file's inode `mtime`, NOT the containing directory's `mtime`. Once the target directory existed, `tgt_logs.stat().st_mtime >= src_logs.stat().st_mtime` remained permanently `True`, skipping updated conversation logs.

### Solution Applied
* Replaced directory `mtime` comparisons with direct verification of `transcript.jsonl` and `transcript_full.jsonl` file modification timestamps.

---
