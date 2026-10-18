# Issue 11: IDE vs. App Title Discrepancy & Title Instability (Language Server Checkpoint Step 23 & Protobuf Tag 1 vs 15 Precedence)

### Symptoms
* **Discrepancy Between Desktop App and IDE**:
  For conversations without markdown artifacts (such as `0a0ae9f4-fb98-4d19-9310-43e3f8f82b15` with authentic title `"Math Calculation Error"`, or `f3c8b32d-2f3b-4691-8e3d-062bc2df9be6`), the IDE initially displayed the authentic model-generated title, while the Desktop App (Hub) displayed generic workspace directory fallbacks (e.g. `".Antigravity Suite Manager Chat"` or `"Conversation"`).
* **Intermittent Loss of Titles in IDE Itself**:
  Even within the IDE, opening, closing, or re-indexing the conversation would periodically cause the title to disappear, revert to raw user prompt text (e.g., `+9++` or shell commands), or collapse into the sanitized workspace fallback name.

---

### Deep Forensic Analysis & Root Causes

#### 1. Where Authentic Titles Are Persisted (`<uuid>.db` Step Type 23)
When generating conversation responses, the Antigravity Language Server periodically generates an authentic title and stores it as a checkpoint inside the conversation's individual SQLite database (`conversations/<uuid>.db`):
* Stored in the `steps` table with `step_type = 23` (`CORTEX_STEP_TYPE_CHECKPOINT`).
* The Protobuf binary payload of `step_payload` contains:
  ```protobuf
  idx: 5, step_type: 23 (CORTEX_STEP_TYPE_CHECKPOINT), status: 3 (DONE)
  Tag 30 (Length-delimited CheckpointMetadata):
    Tag 4 (string): "Math Calculation Error"       # Authentic LLM Generated Title
    Tag 19 (string): "+9++"                         # Initial user prompt
  ```
* In active IDE sessions, the Go Language Server holds this title in RAM and provides it dynamically to the live webview.

#### 2. Why the Desktop App (Hub) Failed to Display the Title
* Unlike the active IDE, the Desktop App reads summary metadata from `~/.gemini/antigravity/conversation_summaries.db` and the fast binary cache `agyhub_summaries_proto.pb`.
* The legacy Python extractor in `extractor.py` inspected **only** markdown files located in `brain/<uuid>/*.md` for `# H1` headings.
* For chats without markdown artifacts (e.g. `0a0ae9f4...` which only contained terminal commands, math computations, or short question-answering), no `*.md` files existed in `brain/<uuid>/`.
* The legacy extractor returned an empty title (`""`). As a result, [title_resolver.py](src/antigravity_suite/history/title_resolver.py) fell back to the sanitized workspace folder name `".Antigravity Suite Manager Chat"`.

#### 3. Why the Title Was Unstable Even in the IDE
* **Redux Selector Priority in `main.js`**:
  Decompiling the IDE's frontend bundle (`jetskiAgent/main.js`) revealed the title resolution expression in the UI renderer:
  ```javascript
  const displayTitle = (item.summary && item.summary.summary) 
    || (item.annotations && item.annotations.title) 
    || "Untitled Conversation";
  ```
  The UI strictly prioritizes **`summary.summary` (Protobuf Tag 1)** over **`annotations.title` (Protobuf Tag 15)**.
  When a chat had no markdown summary, older sync routines fell back to placing the raw initial user prompt (`+9++` or shell commands) into `Tag 1`. Because `summary.summary` takes precedence, the IDE rendered the raw user prompt rather than the authentic title.
* **Volatile Language Server RAM vs. Persistent Disk Storage (`state.vscdb`)**:
  While the conversation is active, the IDE's memory holds the checkpoint title. However, when the IDE restarts, reloads, or fetches state from disk:
  1. The IDE reads `antigravityUnifiedStateSync.trajectorySummaries` from `~/.config/Antigravity IDE/User/globalStorage/state.vscdb`.
  2. If the stored protobuf blob had not been synchronized with the Step 23 title, the IDE overwritten the memory cache with the fallback on disk.

---

### Solution Applied

1. **Protobuf Step 23 Checkpoint Parser**:
   Implemented [parse_step23_checkpoint_title](src/antigravity_suite/history/extractor_checkpoint.py#L13-L56):
   - Queries `steps` where `step_type = 23` ordered by `idx DESC LIMIT 5`.
   - Traverses wire bytes to decode `Tag 30` (Checkpoint Metadata) -> `Tag 4` (Conversation Title).
   - Validates that the extracted title satisfies `is_clean_title()`.

2. **Integration into Extraction Pipeline**:
   Updated [extractor_text.py](src/antigravity_suite/history/extractor_text.py#L65-L86):
   ```python
   brain_dir = find_brain_folder(t_str, db_str)
   title = checkpoint_title or extract_brain_title(brain_dir)
   ```
   Authentic Step 23 titles now take precedence when markdown artifacts are absent.

3. **Strict Protobuf Tag Separation**:
   In [cascade_builder.py](src/antigravity_suite/proto/cascade_builder.py) and [title_sanitizer.py](src/antigravity_suite/history/title_sanitizer.py):
   - **Protobuf Tag 1 (`summary.summary`)**: Receives ONLY the clean sanitized title (e.g. `"Math Calculation Error"`).
   - **Protobuf Tag 2 (`summary.preview`)**: Strictly reserved for user prompt previews (`"+9++"`).
   - **Protobuf Tag 15 (`annotations.title`)**: Synchronized with the clean title.

4. **Multi-Store Synchronization**:
   The merger updates all stores simultaneously:
   - `conversation_summaries.db` (Master SQLite index)
   - `agyhub_summaries_proto.pb` (Desktop App fast binary cache)
   - `state.vscdb` (`trajectorySummaries` for IDE)
   - `annotations/<uuid>.pbtxt` (Persistent disk annotations)

5. **Verification & Audit Trail**:
   Verified via `history_merger_audit.log`:
   ```json
   {"timestamp": "2026-10-18T20:36:00.744137+00:00", "type": "TITLE_CHANGED", "conv_id": "0a0ae9f4-fb98-4d19-9310-43e3f8f82b15", "old_title": "", "new_title": "Math Calculation Error", "reason": "sync_sanitization"}
   ```
   Both Desktop App and IDE now consistently and stably display `"Math Calculation Error"`.

---
