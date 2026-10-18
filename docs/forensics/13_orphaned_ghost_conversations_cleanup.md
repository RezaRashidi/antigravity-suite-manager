# Issue 12: Orphaned Ghost Conversations Cleanup

### Symptoms
* Database contained 304 conversation summaries, but disk contained only 293 valid conversation databases.
* 11 orphaned ghost conversations lingered in SQLite and Protobuf caches.

### Root Cause
* Earlier test executions and manual deletions deleted `.db` files without cleaning `conversation_summaries.db`.

### Solution Applied
* Ran automated audit and purged 11 orphaned conversation records from `conversation_summaries.db`.
* Synchronized `agyhub_summaries_proto.pb` and `state.vscdb`, restoring active conversation count to exactly 293 healthy records.

---
