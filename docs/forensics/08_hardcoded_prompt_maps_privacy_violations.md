# Issue 7: Hardcoded Prompt Maps & Privacy Violations

### Symptoms
* Temporary static map `KNOWN_PROMPT_TITLE_MAP` and regex `PROMPT_PREFIX_PATTERNS` contained raw user prompts.

### Root Cause
* Hardcoded strings were introduced to bypass prompt-as-title bugs without solving the root Protobuf Tag 1 mapping.

### Solution Applied
* Completely purged all hardcoded prompt maps and dictionaries from the entire codebase.
* Replaced with generic algorithmic sanitation in `title_sanitizer.py`.

---
