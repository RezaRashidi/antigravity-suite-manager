# Issue 11: IDE vs. App Title Discrepancy (Language Server Checkpoint Step 23)

### Symptoms
* For conversations without markdown artifacts (e.g. `f3c8b32d-2f3b-4691-8e3d-062bc2df9be6`), the IDE displayed authentic titles (e.g. `"Project Documentation Review And Debugging"`).
* The Desktop App displayed generic directory fallbacks (e.g. `".Antigravity Suite Manager Chat"`).

### Root Cause
* During chat generation, the Antigravity Language Server writes a checkpoint step into `<uuid>.db` with `step_type = 23` (`CORTEX_STEP_TYPE_CHECKPOINT`).
* The Protobuf binary payload of step 23 contains:
  ```protobuf
  idx: 5, step_type: 23 (CORTEX_STEP_TYPE_CHECKPOINT)
  Tag 30:
    Tag 4: "Project Documentation Review And Debugging"  # Authentic LLM Title
    Tag 19: "..."                                        # Initial user prompt
  ```
* IDE reads directly from active Language Server memory and renders `Tag 30 -> Tag 4`.
* The Python extractor in [src/antigravity_suite/history/extractor.py](src/antigravity_suite/history/extractor.py) only inspected `brain/<uuid>/*.md` for `# H1` headings. It never inspected SQLite step 23 checkpoints. When no markdown existed, it returned an empty title, causing [title_resolver.py](src/antigravity_suite/history/title_resolver.py) to fall back to the sanitized workspace folder name `".Antigravity Suite Manager Chat"`.

### Solution Applied
* Added `parse_step23_checkpoint_title` in [src/antigravity_suite/history/extractor.py](src/antigravity_suite/history/extractor.py#L329-L377):
  1. Queries SQLite for steps with `step_type = 23` ordered by index descending.
  2. Decodes Protobuf wire format to extract Tag 30 (Checkpoint Metadata) -> Tag 4 (Conversation Title).
  3. Updates `extract_conv_text()` to prioritize step 23 checkpoint titles over directory fallbacks.

---
