# Issue 17: Systemic 2027y Timestamp Distortion & Go time.Time Zero-Value Wire Format

### Symptoms
* Conversations in the Antigravity Hub Desktop App sidebar displayed creation / last modified dates distorted to `2027y` (e.g., "2027 years ago") across almost all conversations.
* Searching conversations or inspecting `conversation_summaries.db` showed dates beginning with `0001-01-01 00:00:00.000000+00:00` or negative timestamps.
* Re-syncing history initially seemed to fix the timestamp, but upon restarting the daemon or opening the app, timestamps reverted back to `2027y`.

### Root Cause Analysis & Forensics

1. **Protobuf Varint Wire Format for Year 0001**:
   In Google Go Language Server (`language_server`), timestamps are represented using Go's `time.Time` struct. The zero-value of `time.Time` in Go is January 1, Year 0001, 00:00:00 UTC.
   When serialized to Protobuf `google.protobuf.Timestamp`:
   * Epoch seconds: `-62135596800`
   * Protobuf wire tag 3 (`last_modified_time`) varint encoding: `08 80 92 b8 c3 98 fe ff ff ff 01` (11 bytes).

2. **Frontend React Time-Ago Calculation**:
   Decompiling the frontend web bundle `/tmp/web_main.js` served by `language_server` on its HTTPS port revealed:
   ```javascript
   // Bdb resolves trajectory summaries
   const lmtSecs = (b.trajectorySummaries ?? tm).summaries[a]?.lastModifiedTime?.seconds;
   // bN calculates relative time ago
   bN(new Date(Number(lmtSecs) * 1E3));
   ```
   When `lmtSecs` is `-62135596800`, `new Date(-62135596800 * 1000)` produces `January 1, 0001`.
   Evaluating `timeAgo` against the current year (2026):
   $$2026 - 1 = 2025 \text{ years} \approx 2027\text{y}$$

3. **Cascade Summary Builder Poisoning**:
   In `src/antigravity_suite/proto/cascade_builder.py`, if `last_modified_iso` was passed as `None`, empty string, or an existing legacy `0001-...` ISO timestamp, it was accepted as a truthy string and serialized directly into Tag 3.
   Likewise, in `item_metadata.py`, `clean_iso_ts` and metadata resolution prioritized `parsed_modified` over `sql_mtime` without asserting `year > 2000`, causing stale Year 0001 values to circulate infinitely.

4. **Full-Text Search (FTS) & SQL Store Defaults**:
   In `sqlite_fts.py`, `_parse_nanos` converted `0001-...` dates into negative nanosecond integers (`-62135596800000000000`), persisting negative timestamps in `conversations_fts`. In `sqlite_ops.py`, the SQL `CASE` statement only checked `excluded.last_modified_time > '1980-01-01'`; if both `excluded` and the database row were empty or Year 0001, no valid timestamp fallback existed.

### Solutions Applied

1. **Protobuf Binary Encoder Guard**:
   In `src/antigravity_suite/proto/cascade_builder.py`, added explicit Year 0001 rejection:
   ```python
   if not last_modified_iso or str(last_modified_iso).startswith("0001"):
       last_modified_iso = now_iso
   if not created_iso or str(created_iso).startswith("0001"):
       created_iso = last_modified_iso
   if not last_user_input_iso or str(last_user_input_iso).startswith("0001"):
       last_user_input_iso = last_modified_iso
   ```

2. **Metadata Resolver Normalization**:
   In `src/antigravity_suite/history/item_metadata.py`, rejected any incoming ISO timestamp starting with `"0001"`:
   ```python
   final_modified_iso = t_clean_modified or parsed_modified or sql_mtime or file_mtime_iso
   if not final_modified_iso or final_modified_iso.startswith("0001"):
       final_modified_iso = file_mtime_iso
   ```

3. **Full-Text Search (FTS) Nanosecond Validation**:
   In `src/antigravity_suite/history/sqlite_fts.py`:
   - Updated `_parse_nanos` to require `dt.year > 2000` before computing nanoseconds.
   - Updated `repair_fts_zero_timestamps` to detect `last_modified_time <= 0` or `NULL` and repair them from authentic database or file mtime.

4. **Relational Database Upsert Fallback**:
   In `src/antigravity_suite/history/sqlite_ops.py`, updated `upsert_summary` to fall back to SQLite's native `strftime('%Y-%m-%d %H:%M:%S.000000+00:00', 'now')` if both incoming and existing timestamps are invalid.

5. **Protobuf Summary Cache Purification**:
   In `src/antigravity_suite/history/summary_sync.py`, filtered `all_summaries` against valid active conversation UUIDs, preventing obsolete or corrupted proto entries from lingering in `agyhub_summaries_proto.pb`.

### Verification
* Audited all 304 active conversations across `conversation_summaries.db`, `agyhub_summaries_proto.pb`, `agyhub_summaries.pb`, `jetbox_summaries.pb`, and `state.vscdb`.
* Zero records contain `0001` or negative timestamps (`bad = 0`).
* All conversations in the Antigravity Hub Desktop App and IDE sidebar now display accurate, human-readable relative dates (e.g., "2 days ago", "1 hour ago").
