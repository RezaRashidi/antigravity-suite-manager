# Issue 65: Concurrent Chat Model Clobbering, Argon Quota Collision & Context Summarization 10MB Proxy Body Limit

## 1. Problem Statement
Three interconnected failures occurred under concurrent multi-account usage and large-context sessions:
1. **Concurrent Chat Model & Catalog Clobbering (`unknown model key MODEL_PLACEHOLDER_M525: model not found`):**
   When two chats ran simultaneously across accounts of different tiers (e.g., Paid Pro `Gemini 4 Hydrogen (High)` / `MODEL_PLACEHOLDER_M525` in chat A and Free `Gemini 3.8 Flash` in chat B), whichever chat finished first caused the other chat's model dropdown and `bindings.json` model to change, or crashed Language Server inside `staticCatalog.GetModelInfoFromKey` with `unknown model key MODEL_PLACEHOLDER_M525: model not found`.
2. **Missing/Colliding `Gemini 4 Argon` Quota Bucket:**
   Paid Pro accounts return three quota groups from `/v1internal:retrieveUserQuotaSummary` (`Gemini Models`, `Claude and GPT models`, and `Gemini 4 Argon`), but `Gemini 4 Argon` (`gemini-argon-wtu-weekly`) collided with `gemini:weekly` and was omitted from UI flyout display and disk persistence.
3. **Context Summarization `connection reset by peer` on Large Chats:**
   During `pre-invocation hook: context summarization` on long trajectories, Language Server failed with `Post "http://localhost:50999/v1internal:streamGenerateContent?alt=sse": read: connection reset by peer`.

## 2. Root Cause Analysis
1. **`fetchAvailableModels` Hijacking & Catalog Overwrite (`bin/lib/patch/router/server.js`):**
   - Requests to `/v1internal:fetchAvailableModels` carry `{}` (no `cascadeId`). `server.js` fell back to `_lastCascadeId` (`freshLastId`), routing global IDE model refreshes through whichever background chat or Free-tier subagent ran most recently.
   - Because `language_server` stores one shared in-memory model catalog across all chats, receiving a Free-tier 22-model response erased Paid Pro model definitions (`MODEL_PLACEHOLDER_M525`) while another Paid Pro chat was mid-execution.
   - Internal background calls (`gemini-4-hydrogen-sonar`, `tab_*`, `gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`) also bypassed the single `gemini-3.5-flash-lite` guard and overwrote `bindings[cascadeId].model`.
2. **UI Restoration Race & Passive Dropdown Overwrite (`bin/lib/patch/multi_account_ui.js`, `bin/lib/patch/ui/mount.js`):**
   - `handleChatModelRestoration` only slept `120ms` before reading `window.__antigravityAvailableConfigs`, racing ahead of `triggerDynamicModelRefresh()` (which could take `700ms–2600ms`), failing validation against stale configs, and saving the fallback model (`Gemini 3.8 Flash`) over the chat's binding.
   - `checkPillAndCascade()` (running on `MutationObserver` and a 2.5s interval) unconditionally persisted any `curModel !== saved` DOM transition triggered by background Redux `userStatus/setUserStatus` updates from another concurrent chat.
   - `__antigravityDetectCascadeId` checked sidebar selection (`selId`) ahead of the owning `[data-testid="conversation-view"]` container (`cvId`).
   - Unfocused background windows could call `set-active` during passive `render()`.
3. **Argon Bucket Key Collision & Non-Persisted Quotas (`telemetry.js`, `flyout.js`, `multi_account_router.js`):**
   - `parseGroupsToBuckets` classified `Gemini 4 Argon` under `fam = 'gemini'` via `.includes('Gemini')`, colliding with `gemini:weekly` in `seen` deduplication.
   - `flyout.js` lacked an `argon` render group, and `refreshQuotasAsync` wrote tier/models to `<email>.json` without persisting `acc.quotas`.
4. **Hardcoded `10 MB` Request Body Cap (`vendor/antigravity-model-proxy/dist/proxy.js`):**
   - `main.log` showed `[Proxy] Request body exceeds 10MB limit (POST /v1internal:streamGenerateContent?alt=sse)` during context summarization on long trajectories.
   - Reaching `MAX_BODY_SIZE = 10 * 1024 * 1024` invoked `req.destroy()` immediately before sending an HTTP response, causing Go's HTTP client to report `connection reset by peer`, while `proxyReq.setTimeout(60000)` sat below `server.js`'s `120s` TTFB timeout.

## 3. Resolution
1. **Router Isolation & Superset Model Catalog Preservation (`bin/lib/patch/router/server.js`, `telemetry.js`):**
   - Excluded `isModelListRpc` from `freshLastId` fallback so payload-less `/v1internal:fetchAvailableModels` requests remain scoped to `activeDefault`.
   - Added `_knownModelCatalog`, `updateModelCatalogCache`, and `mergeModelCatalogResponse` (seeded both from HTTP 200 `/v1internal:fetchAvailableModels` responses and background `fetchAccountModels` calls) to retain missing Paid Pro model definitions in `parsed.models` (with `recommended: false`) while keeping `agentModelSorts` and `groupedModels` scoped to the active account.
   - Extended `isInternalBackgroundModel` filtering to skip clobbering `existingModel` for `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`, `gemini-4-hydrogen-sonar`, and `tab_*` models.
   - Wrapped `req.on('end', async () => ...)` in `try/catch` to return HTTP `502` JSON rather than dropping sockets on unexpected errors.
2. **Frontend Restoration Synchronization & Passive Guard (`bin/lib/patch/ui/mount.js`, `multi_account_ui.js`):**
   - Prioritized `cvId` over `selId` in `__antigravityDetectCascadeId`, tracked `window.__antigravityActiveRefreshPromise` in `triggerDynamicModelRefresh`, and filtered out `cfg.disabled` in `isModelValidInConfigs`.
   - Updated `handleChatModelRestoration` to await `__antigravityActiveRefreshPromise` (bounded to `2.5s`) and verify sequence/chat ID consistency before restoring or binding.
   - Added capture-phase `pointerdown` tracking (`lastUserModelClickTs`) so `checkPillAndCascade` never overwrites an existing `saved` model from passive React updates without a recent user interaction with the model menu, and scoped passive `binding-sync` / focus synchronization to focused windows (`document.hasFocus()`).
3. **Argon Quota Separation & Persistence (`telemetry.js`, `flyout.js`, `multi_account_router.js`):**
   - Classified `Gemini 4 Argon` groups as `family: 'argon'` and added a dedicated `Gemini 4 Argon` group in `flyout.js`.
   - Persisted `cur.quotas = acc.quotas` in `refreshQuotasAsync`.
4. **Loopback Proxy Body Limit & Timeout Increase (`vendor/antigravity-model-proxy/dist/proxy.js`):**
   - Raised `MAX_BODY_SIZE` from `10 MB` to `128 MB`, wrote the `413` JSON response before calling `req.destroy()`, and matched `proxyReq.setTimeout` to `120000 ms`.
   - Re-deployed updated patches to `/opt/Antigravity-x64/resources/app.asar` via `manage-antigravity.sh patch-models app --force`.

## 4. Verification
- Added `tests/test_concurrent_chats_isolation.js` covering `argon` quota separation, `fetchAvailableModels` isolation and catalog retention, background Sonar non-clobbering, UI restoration wait, and passive clobber prevention.
- Verified JS syntax (`node -c`) on all modified files including `vendor/antigravity-model-proxy/dist/proxy.js`.
- Verified JS test suites: `test_concurrent_chats_isolation.js`, `test_chat_switch_model_refresh.js`, `test_typing_performance_isolation.js`, `HOME=/tmp node tests/test_router_health_failover.js`, `test_subagent_router.js`, `test_router_quota_routing.js`, and `test_eligibility_middleware.js` all passed.
- Verified `app.asar` contains `MAX_BODY_SIZE = 128 * 1024 * 1024`, `mergeModelCatalogResponse`, `lastUserModelClickTs`, `__antigravityActiveRefreshPromise`, and `Gemini 4 Argon`.
