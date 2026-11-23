# Forensic Analysis: Cross-Chat Model Clobbering During Concurrent Generation

## 1. Problem Statement
When a user begins generating a response in Chat A with one model (e.g. `Gemini 2.5 Pro`), then switches to Chat B and changes the model to another option (e.g. `Gemini 2.5 Flash`), Chat A's active model was unexpectedly overwritten with Chat B's model while Chat A was still actively executing.

## 2. Root Cause Analysis
Forensic investigation across the frontend DOM event listeners, restoration routines, and router reverse proxy exposed three concurrent leakage vectors:

### A. Unscoped Click Timestamp in UI Controller (`bin/lib/patch/multi_account_ui.js`)
- `lastUserModelClickTs` was tracked as a global scalar timestamp without recording the conversation ID where the user actually clicked (`lastUserModelClickCid`).
- When the user opened the model selector dropdown in Chat B, `lastUserModelClickTs` was set.
- Upon switching back to Chat A within 3 seconds, `checkPillAndCascade()` ran.
- Because `(Date.now() - lastUserModelClickTs) < 3000` evaluated to `true` across all conversations, and Chat A's DOM trigger temporarily reflected Chat B's model text during view transition, `checkPillAndCascade()` incorrectly identified Chat A as having just undergone a user model selection.
- Furthermore, `(!saved || userSelectedModelRecently)` allowed unseeded chats to passively adopt whatever model lingered in the DOM trigger from previous tabs.

### B. Trigger Dropdown Failure Fallback in Restoration (`bin/lib/patch/ui/mount.js`)
- In `__antigravitySelectModel(targetModelName, availableConfigs)`:
  - If Chat A was actively generating responses, the Radix UI model selector dropdown was either disabled, busy, or failed to open within 70ms, resulting in `items.length === 0`.
  - When no items were found, the function executed `return current || null;`.
  - `current` was the DOM text currently visible on the trigger (Chat B's model).
  - Consequently, `handleChatModelRestoration(cid)` in `multi_account_ui.js` received `restored = current` and unconditionally wrote `state.bindings[cid].model = restored` and dispatched `/api/multi-account/bind`, overwriting Chat A's database binding with Chat B's model.
  - Additionally, if `targetModelName` was temporarily absent in configs during account switching, line 273 fell back to `current` (Chat B's model) rather than a configured account fallback.

### C. Proxy Router Generation Auto-Bind Clobber (`bin/lib/patch/router/server.js`)
- In `server.js` lines 257-266, `streamGenerateContent` intercepted the incoming generation model:
  ```javascript
  if (!isInternalBackgroundModel(requestedModel) || !existingModel) {
      setBinding(cascadeId, targetEmail, requestedModel);
  }
  ```
- Because `!isInternalBackgroundModel(requestedModel)` was `true` for standard production models, any background generation or unpinned RPC call arriving with a different model clobbered `existingModel` in `bindings.json`.

## 3. Implementation Details

### A. Conversation-Scoped User Click Tracking (`multi_account_ui.js`)
- Added `lastUserModelClickCid` alongside `lastUserModelClickTs`.
- On `pointerdown` over the model selector trigger or dropdown items, both timestamp and current `cascadeId` are recorded.
- In `checkPillAndCascade()`, `userSelectedModelRecently` now strictly checks:
  ```javascript
  const userSelectedModelRecently = (lastUserModelClickCid === c) && (Date.now() - lastUserModelClickTs < 3000);
  if (curModel && curModel !== saved && userSelectedModelRecently) {
      persistChatModel(c, curModel);
  }
  ```
- Removed `!saved` auto-persistence to prevent chats from passively adopting models from previous tabs.
- In `handleChatModelRestoration(cid)`, added `shouldPersist` guard: bindings are only updated if `restored` matches `savedModel` or represents an explicit fallback when `savedModel` is genuinely unsupported by the active account.

### B. Safe Restoration & Busy State Guard (`ui/mount.js`)
- In `__antigravitySelectModel(targetModelName, availableConfigs)`:
  - When `targetModelName` is provided, `chosenTarget` preserves `targetModelName`. It never falls back to `current` (the other chat's DOM text).
  - If the dropdown fails to open (`items.length === 0`), it sends `Escape` and returns `null` (never `current`).
  - When `matchedItem` is not found and the requested model was valid, it returns `null` instead of arbitrarily clicking a random fallback item or `items[0]`.

### C. Router Model Immutability Guard (`router/server.js`)
- In `server.js`, updated `isGen` model binding check:
  ```javascript
  if (!existingModel && !isInternalBackgroundModel(requestedModel)) {
      const targetEmail = (boundEmail && boundEmail !== 'Primary (Native)') ? boundEmail : null;
      setBinding(cascadeId, targetEmail, requestedModel);
  }
  ```
- An explicit user binding in `bindings.json` cannot be clobbered by background generation requests.

### D. Keyring Test Sandbox Isolation (`router/accounts.js`)
- In `readTokenFromKeyring()` and `loadAllAccounts()`, enforced `if (process.env.ANTIGRAVITY_TEST) return null;` to prevent test suites from accessing local host DBus/Keyring credentials.

## 4. Verification & Testing
- Updated `tests/test_concurrent_chats_isolation.js` with:
  1. Router generation model overwrite prevention under concurrent streaming.
  2. Cross-chat click isolation verifying that selecting a model in Chat B does not persist into Chat A upon rapid switching while Chat A is busy.
  3. `mount.js` `__antigravitySelectModel` returning `null` when dropdown is busy/unopened during generation.
- Re-ran all test suites:
  - `tests/test_concurrent_chats_isolation.js`: PASSED
  - `tests/test_chat_switch_model_refresh.js`: PASSED
  - `tests/test_typing_performance_isolation.js`: PASSED
  - `tests/test_router_health_failover.js`: PASSED
  - `tests/test_multi_account_ipc_patch.js`: PASSED
  - `tests/test_subagent_router.js`: PASSED
  - All 264 Python unit tests: PASSED
- Deployed patches live to `/opt/antigravity` (IDE) and `/opt/antigravity2` (App).
