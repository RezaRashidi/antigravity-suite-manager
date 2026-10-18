# Issue 3: Rogue Symlink Causing Schema Version Crash

### Symptoms
* Go Language Server log contained recurring warnings:
  ```
  Skipping conversation conversation_summaries while listing: open backend ~/.gemini/antigravity/conversations/conversation_summaries.db: db version too new: got 3, want 1
  [Summaries] failed to generate summary for conversation_summaries while reconciling: conversation conversation_summaries not found
  ```

### Diagnostic Methodology & Execution
* Checked directory contents of `~/.gemini/antigravity/conversations/`.
* Discovered a rogue symlink:
  ```bash
  ~/.gemini/antigravity/conversations/conversation_summaries.db -> ../conversation_summaries.db
  ```
* **Root Cause**: The Go Language Server enumerates all `*.db` files in `conversations/` assuming they are individual conversation trajectory databases (`user_version = 1`). It attempted to open the master summary database (`user_version = 3`) as a conversation, threw a schema incompatibility error, and aborted reconciliation for that thread.

### Solution Applied
* Removed the rogue symlink:
  ```bash
  rm -f ~/.gemini/antigravity/conversations/conversation_summaries.db
  ```
* Removed empty 0-byte collision artifact `~/.config/antigravity/conversation_summaries.db`.

---
