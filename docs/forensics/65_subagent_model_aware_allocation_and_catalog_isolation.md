# Issue 63: Subagent Model-Aware Account Allocation, Language Server Catalog Clobbering & Monitor Model Protection

## 1. Problem Statement
When running a Paid Pro account (e.g., `risaai315@gmail.com`) with tiered models such as `Gemini 4 Carbon (High)` (`MODEL_PLACEHOLDER_M427` / `gemini-4-carbon-high`), multi-turn execution succeeded initially, then crashed mid-execution inside Antigravity Language Server with:
```
Agent execution terminated due to error.
unknown model key MODEL_PLACEHOLDER_M427: model not found
```
Additionally, the UI model dropdown for `risaai315@gmail.com` reverted to the Free Pro flat model list (missing `Low`/`Medium`/`High` tiers) until switching away from and back to the account.

## 2. Root Cause Analysis
1. **Unchecked Cross-Account Subagent Leasing (`subagent_allocator.js`):**
   - `allocateAccountForSubagent` leased idle non-parent accounts solely by load/quota without verifying whether the peer account supported the subagent/parent model (`available_models` / `available_model_ids`).
   - Paid-tier variants like `Gemini 4 Carbon (High)` or unlisted `gemini-pro-orchestrator` were routed onto Free Pro accounts (or Paid peers lacking Carbon tiers), triggering `HTTP 404 (model_not_found)` failover and polluting `_subagentLeases`.
2. **Global `fetchAvailableModels` Registry Clobbering (`server.js`):**
   - Antigravity `language_server` maintains a single global in-memory model catalog (`cascadeModelConfigData`).
   - When a subagent allocated to a Free Pro account called `/v1internal:fetchAvailableModels`, the Free Pro response overwrote the Language Server catalog, erasing `MODEL_PLACEHOLDER_M427` for both subagents and the parent Paid Pro chat.
3. **Global Account Quarantine on `HTTP 404` & Background Monitor Binding Clobbering:**
   - Upstream `404 model_not_found` called `markAccountUnhealthy`, needlessly sidelining healthy Free Pro accounts for 30 minutes across all models instead of recording per-(account, model) incompatibility.
   - Background safety monitor calls (`gemini-3.5-flash-lite`) went through `isGen` binding sniffing and overwrote `bindings[cascadeId].model`, hiding the chat's true model from downstream subagent checks.

## 3. Resolution
1. **Model Compatibility Verification & Per-Model 404 Memory (`bin/lib/patch/router/accounts.js`, `telemetry.js`, `multi_account_router.js`):**
   - Added `normalizeModelKey`, `accountSupportsModel`, `markModelUnsupported`, and `clearUnsupportedModels` in `accounts.js`.
   - Updated `fetchAccountModels` (`telemetry.js`) and persistence (`multi_account_router.js`) to retain `available_model_ids` alongside `available_models` display names.
   - Updated `pickHealthyFallbackAccount` to filter candidates by `accountSupportsModel`.
2. **Model-Aware Subagent Allocation (`bin/lib/patch/router/subagent_allocator.js`):**
   - Resolved `effectiveModel` from `requestedModel`, subagent binding, or parent binding (ignoring `gemini-3.5-flash-lite` monitor noise when a chat model exists).
   - Validated cached `_subagentLeases` against `effectiveModel` and restricted peer switching exclusively to healthy accounts supporting the model. If no other healthy account supports the model, subagents remain on the parent account.
3. **Catalog & Binding Isolation (`bin/lib/patch/router/server.js`):**
   - Routed subagent `/v1internal:fetchAvailableModels` RPCs through the parent/active account so subagents never overwrite Language Server's global model catalog with a narrower Free Pro list.
   - Prevented `gemini-3.5-flash-lite` monitor calls from overwriting an existing chat model binding.
   - Switched `model_not_found` (`404`) handling from global account quarantine to `markModelUnsupported` + `releaseSubagentLease`, preferring `parentEmail` during subagent failover.

## 4. Verification
- Added model-aware subagent allocation tests (`subagent kept on parent`, `unlisted orchestrator kept on parent`, `shared model switches`) in `tests/test_subagent_router.js`.
- Added end-to-end HTTP router checks (monitor non-clobbering, subagent `fetchAvailableModels` parent retention, and Carbon High parent retention) in `tests/test_router_health_failover.js`.
- Verified syntax (`node --check`), all Node router tests (`test_subagent_router.js`, `test_router_health_failover.js`, `test_router_quota_routing.js`), and Python suites (`test_patch_subagents.py`, `test_fixes_validation.py`).
