# Issue 9: Pinned Chats Displaying "2027y" (Year-1 / Epoch 0 Timestamp Bug)

### Symptoms
* In Antigravity Desktop App, pinned conversations (such as "Monitoring Queue Performance Dashboard") displayed relative timestamps of "2027y" (e.g. 2027 years ago) instead of recent days.
* Restarting Antigravity temporarily masked the issue, but subsequent history sync runs reintroduced the corrupt timestamp.

### Root Cause
* In [src/antigravity_suite/history/item_metadata.py](src/antigravity_suite/history/item_metadata.py) and [src/antigravity_suite/history/sqlite_store.py](src/antigravity_suite/history/sqlite_store.py), when a conversation was pinned or metadata was extracted:
  - If `last_modified` was missing, 0, or evaluated as falsy in SQLite schema definitions, it defaulted or fell back to 0 or epoch seconds.
  - When the Language Server or frontend formatted millisecond timestamps, an epoch 0 or negative relative delta was parsed as year 1 BC / 1970 relative to current year 2026/2027, displaying `2027y`.
  - The extraction pipeline lacked a strict floor validation for timestamps.

### Solution Applied
* Implemented monotonic timestamp sanitization in [src/antigravity_suite/history/item_metadata.py](src/antigravity_suite/history/item_metadata.py#L30-L58):
  1. Validates that `last_modified` is positive and exceeds minimum epoch threshold (`1577836800000` = Jan 1, 2020).
  2. Falls back to transcript file `os.path.getmtime()` or current system time in milliseconds (`int(time.time() * 1000)`).
  3. Enforced timestamp validation in SQLite updates ([src/antigravity_suite/history/sqlite_store.py](src/antigravity_suite/history/sqlite_store.py#L219-L232)).

---
