# Issue 5: User Prompt Leaking into Conversation Titles & Bubbles

### Symptoms
* Conversation titles in IDE displayed raw user prompts or shell commands (e.g., `curl ...`, raw multi-line questions) instead of clean topic titles.
* Renaming or re-opening conversations in the IDE reverted them back to the raw prompt text.

### Diagnostic Methodology & Execution (Step-by-Step Investigation)

#### Step 1: Discovering the Active Webview Server Port & CSRF Token
The IDE UI does not load local disk HTML/JS directly; it proxies through a local loopback TLS server hosted by `language_server_linux_x64.bin`:
```bash
ps aux | grep -E "language_server.*antigravity-ide" | grep -v grep
```
Extracted arguments:
- `--extension_server_port=34823`
- `--csrf_token=940dddbd-4458-4df4-91c9-9517bfc2560d`
- `--app_data_dir=antigravity-ide`

#### Step 2: Extracting the Live Frontend JavaScript Bundle (`main.js`)
Downloaded the active React Webview bundle directly from the Go Language Server loopback HTTP listener:
```bash
curl -k -s -H "x-codeium-csrf-token: 940dddbd-4458-4df4-91c9-9517bfc2560d" \
  https://127.0.0.1:34823/jetskiAgent/main.js -o /tmp/jetski_main.js
```

#### Step 3: Deminifying and Tracing the Title Rendering AST
Searched `/tmp/jetski_main.js` for conversation title resolution patterns:
```bash
grep -o -E '.{0,50}(annotations\.title|summary\.summary).{0,50}' /tmp/jetski_main.js
```
Discovered the core title selector expression inside the Redux UI renderer:
```javascript
// Extracted from jetskiAgent/main.js
const displayTitle = (item.summary && item.summary.summary) 
  || (item.annotations && item.annotations.title) 
  || "Untitled Conversation";
```
**The Critical Revelation**:
The UI prioritizes **`summary.summary` (Protobuf Tag 1)** ABOVE **`annotations.title` (Protobuf Tag 15)**.
Even if `annotations.title` contained a clean title, if `summary.summary` contained ANY string, the UI displayed `summary.summary`!

#### Step 4: Dissecting the Binary Wire Format (`raw_summary`)
Inspected how `raw_summary` in SQLite `conversation_summaries.db` was being assembled:
```python
import os, sqlite3
from antigravity_suite.proto.cascade import parse_cascade_summary

db_file = os.path.expanduser("~/.gemini/antigravity/conversation_summaries.db")
con = sqlite3.connect(db_file)
row = con.execute("SELECT conversation_id, raw_summary FROM conversation_summaries WHERE app_data_dir = 'antigravity-ide' LIMIT 1").fetchone()
parsed = parse_cascade_summary(row[1])
print("Tag 1 (summary.summary):", parsed.get("summary"))
print("Tag 2 (summary.preview):", parsed.get("preview"))
print("Tag 15 (annotations.title):", parsed.get("title"))
```
**Result**:
- `Tag 1 (summary.summary)` was populated with `ext_p` (the user's first prompt text, e.g., `"curl -s http://..."` or `"why are my chats not syncing..."`)!
- When no markdown summary existed in `~/.gemini/antigravity/brain/<uuid>/*.md`, the legacy resolver fell back to assigning the user prompt to Tag 1.
- Because Tag 1 took precedence in `main.js`, the entire IDE rendered the raw prompt as the title.

### Solution Applied
* Implemented generic title resolution in [src/antigravity_suite/history/title_sanitizer.py](src/antigravity_suite/history/title_sanitizer.py):
  1. Priority order: Existing clean title > Authentic LLM summary > Clean artifact title > Workspace-derived title (`<WorkspaceName> Chat`) > `"Conversation"`.
  2. Strips Markdown context tokens (`@[filename]` and `in @[filepath]`).
  3. **Strict separation of Protobuf fields**:
     - **Protobuf Tag 1 (`summary.summary`)**: Receives ONLY the clean sanitized title (e.g., `"Optimizing Ansible Dragonfly Role"`).
     - **Protobuf Tag 2 (`summary.preview`)**: Strictly reserved for user prompt previews.
     - **Protobuf Tag 15 (`annotations.title`)**: Synchronized with the clean title.

---
