# Issue 10: Asymmetric Chat Deletion & Infinite Loading Spinner

### Symptoms
* Deleting a conversation in the Desktop App correctly propagated and removed it from IDE.
* Deleting a conversation in the IDE did NOT remove it from the Desktop App.
* Clicking on the deleted conversation in the Desktop App left the application in a permanent, infinite loading spinner.

### Root Cause
* Asymmetric deletion detection in [src/antigravity_suite/history/deletion.py](src/antigravity_suite/history/deletion.py) and [src/antigravity_suite/history/watcher.py](src/antigravity_suite/history/watcher.py):
  1. Deletion handling only tracked events originating from App's `app_storage.json` or local App unlinks.
  2. When IDE deleted a conversation, the backing `.db` file in `~/.gemini/antigravity/conversations/<uuid>.db` was deleted by the IDE Language Server.
  3. However, `conversation_summaries.db`, `agyhub_summaries_proto.pb`, and cascade annotations retained the summary entry.
  4. The Desktop App sidebar still rendered the conversation from `agyhub_summaries_proto.pb`. When the user clicked it, the App requested the deleted `<uuid>.db` from the Language Server, which failed silently and hung the UI in an infinite loading spinner.

### Solution Applied
* Implemented bidirectional active deletion and tombstone synchronization:
  1. In [src/antigravity_suite/history/deletion.py](src/antigravity_suite/history/deletion.py#L705-L713), added validation that automatically purges orphaned records from `conversation_summaries.db`, `agyhub_summaries_proto.pb`, and `annotations/<uuid>.pbtxt` whenever `<uuid>.db` is absent.
  2. Updated [src/antigravity_suite/history/watcher.py](src/antigravity_suite/history/watcher.py#L253-L270) to detect unlinks in `conversations/` and immediately broadcast removal across both App and IDE stores.

---
