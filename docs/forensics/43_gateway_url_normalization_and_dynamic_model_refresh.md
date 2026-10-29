# Forensics Case 43: Gateway Base URL Normalization, Dynamic Model Refresh, and Subagent Audit Fixes

## 1. Executive Summary
- **User Requests**:
  1. Default Gateway Base URL to `https://api.example.com/v1/` and automatically append necessary endpoints (`/chat/completions`, `/models`, etc.) without requiring user path manipulation.
  2. Full codebase audit across custom model proxy, translators, UI injection, and IPC to ensure zero bugs or unhandled edge cases.
  3. Redesign the model selector update mechanism so it is dynamic and non-destructive: do NOT kill/restart the Language Server, do NOT reload the window or disrupt in-flight chats, active subagents, or running tasks.
- **Root Causes Discovered**:
  1. **Destructive Sync Mechanism**: In Case 41, `storage:sync-models` used `ls.restartLanguageServer()` and `win.loadURL(newUrl)` / `win.webContents.reload()`. This killed the Go language server process and reloaded webContents, crashing active LLM generation streams, terminating background subagents, and erasing editor drafts.
  2. **URL Construction Trailing Slash Inconsistencies**: Gateway Base URL defaulted to `https://api.example.com/v1` without a trailing slash. Appending `/chat/completions` or `/models` in various modules lacked multi-slash collapsing (`/+/g`), causing double slashes (`//models`) or path truncation if users entered trailing slashes.
  3. **Silent Model Deletion Failure**: `modelStore.delete(name)` filtered strictly by exact string matching without normalizing the `models/` prefix. Un-prefixed model names (`odirect/gpt-4o`) silently failed to delete while reporting success.
  4. **Batch Import Name Collisions**: In `autoImportFreeModels` and `Add Selected Models`, `uniqueName()` checked against a stale in-memory array (`modelList`), resulting in duplicate key errors on batch import.
  5. **Context Window vs Output Token Clamping**: When gateways reported `max_tokens >= context_length`, `validateCustomModel` rejected models with `'maxOutputTokens must be smaller than contextWindow'`.
  6. **Missing Reasoning History Persistence**: `modelReasoningContent` in `shared.js` was queried in `mapGeminiToOpenAI` but was never set upon stream or non-stream completion, losing reasoning history on multi-turn conversations.
  7. **Discarded Error Bodies**: `customRequest.js` discarded upstream error responses immediately (`upstream.destroy()`) without reading error bodies, masking upstream provider diagnostics.

---

## 2. Technical Architecture & Resolution

### 2.1 Dynamic In-Memory Model Synchronization (Zero Downtime)
Antigravity's chat UI stores models in Redux Toolkit state (`userStatus.cascadeModelConfigData.clientModelConfigs`), synced via `getUserStatus()` RPC:
1. **ConnectRPC Refresh**: When models change, `customIpc.js` calls `LanguageServerService/GetAvailableModels` with `{ forceRefresh: true }` via local ConnectRPC. The proxy intercepts `/v1internal:fetchAvailableModels`, injects the updated models, and Go updates its catalog in memory without restarting.
2. **UserStatus Retrieval**: Queries `LanguageServerService/GetUserStatus` over loopback to fetch the updated `userStatus` object.
3. **In-Memory Redux Dispatch**: Injects a lightweight script into all open windows (`executeJavaScript`):
   - Traverses React Fiber from `#root` to locate the Redux `store`.
   - Dispatches `{ type: 'userStatus/setUserStatus', payload: userStatus }`.
   - Dispatches `'agy-models-changed'` CustomEvent.
4. **Result**: Dropdown updates in <50ms. Zero process restarts, zero window reloads, zero aborted streams.

### 2.2 Gateway Base URL Normalization & Automatic Path Appending
1. **Defaults**: Updated default gateway URL across `customPreload.js` and `modelManagement.js` to `https://api.example.com/v1/`.
2. **Multi-Slash Collapsing**:
   - `registry.js`: `url.pathname.replace(/\/+/g, '/').replace(/\/+$/, '')`
   - `google.js`: `url.pathname.replace(/\/+/g, '/').replace(/\/+$/, '').replace(/:(?:streamGenerateContent|generateContent)$/, '')`
3. **Automatic Path Appending**: In `customRequest.js`, if a model URL lacks a completion or model endpoint suffix (`/chat/completions`, `/messages`, `/models/...`), the proxy routes it through `registry.getProviderUrl` to append the appropriate path automatically.

### 2.3 Additional Bug Fixes
- **Model Deletion**: Normalized target in `modelStore.delete(name)` with `name.startsWith('models/') ? name : 'models/' + name`.
- **Batch Name Allocation**: Added in-loop `allocatedNames` tracking in `customPreload.js` to eliminate batch import collision errors.
- **Output Token Clamping**: Clamped `maxOutputTokens` to 75% of `contextWindow` when `maxOutputTokens >= contextWindow`.
- **Reasoning Content Persistence**: Stored `accumulatedReasoning` into `modelReasoningContent` on stream and non-stream completion in `openai.js`.
- **Upstream Error Capture**: Read up to 4KB of upstream error response body in `customRequest.js` for descriptive error reporting.

---

## 3. Verification & Validation
1. **Pytest**: 219 tests passed (100% pass rate) including `test_gateway_url_and_dynamic_sync.py`.
2. **Packaging**: Successfully built and patched into `/opt/Antigravity-x64/resources/app.asar` with `./manage-antigravity.sh patch-models --force`.
3. **Coexistence**: Verified coexistence of RTL patch, F5 reload patch, multi-account selector patch, and custom models patch.
4. **Style Constraints**: All Python and Bash files verified `<= 100 lines`.
