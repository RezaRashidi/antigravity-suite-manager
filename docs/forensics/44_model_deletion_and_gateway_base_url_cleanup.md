# Case 44: Model Deletion Invalidation, Gateway Base URL Normalization & Patch Verification

## 1. Incident Overview
- **User Symptoms**:
  1. Deleted model (`oc/jev`) remained visible in the Chat model selector dropdown even after clicking "Delete" in the Settings panel.
  2. The full endpoint URL (`https://ai.odirect.app/v1/chat/completions`) was written and displayed in Gateway configurations, group headers, and provider presets instead of the clean base URL form (`https://ai.odirect.app/v1/`).
  3. Requested a forensic audit of the patch pipeline to ensure all fixes are correctly compiled and applied to `/opt/Antigravity-x64/resources/app.asar`.

---

## 2. Root Cause Analysis
1. **Asymmetric Model Deletion in IPC Layer**:
   - In `customIpc.js`, `storage:delete-custom-model` called `manager.store.delete(name)` and sent `win.webContents.send('storage:models-changed')`, but did NOT execute Language Server RPC cache invalidation (`GetAvailableModels{forceRefresh: true}`) or synchronous React Redux store re-hydration.
   - When the renderer's `storage:models-changed` listener triggered `refreshChatModelSelectorDynamically`, it immediately called `GetUserStatus` against the Language Server without first forcing a model refresh. The Language Server returned its stale in-memory cached model list (still containing `oc/jev`), which was re-dispatched into Redux.
   - `customModelsCache` in `customPreload.js` possessed a 30-second TTL that was not cleared when `storage:models-changed` was received in non-initiator windows.
2. **Persistent Full-Endpoint Gateway URLs**:
   - Upstream presets in `providers.js` and default fallbacks in `modelStore.js` explicitly appended `/chat/completions` or `/messages` to `defaultUrl` and `apiUrl`.
   - In `openConfigureGateway`, `openAddGatewayModal`, and `openModelModal`, existing URLs containing `/chat/completions` were displayed as-is without stripping the endpoint suffix.
   - All 19 configured models in `~/.gemini/antigravity/custom_models.json` had persisted `"apiUrl": "https://ai.odirect.app/v1/chat/completions"` from legacy imports.

---

## 3. Implemented Fixes
1. **Unified URL Base Normalizer (`normalizeBaseUrl`)**:
   - Implemented in `modelStore.js` and `customPreload.js`:
     - Strips hash fragments and query parameters (`url.split(/[?#]/)[0]`).
     - Strips trailing endpoints (`/chat/completions`, `/completions`, `/messages`, `/models`, `:streamGenerateContent`, `:generateContent`).
     - Ensures clean, standardized base URL with trailing slash (e.g. `https://ai.odirect.app/v1/`).
   - Cleaned all default provider presets in `providers.js`.
   - Automatically normalizes `apiUrl` in `store.save`, `store.import`, `openConfigureGateway`, `openAddGatewayModal`, and `autoImportFreeModels`.
2. **Multi-Identifier Model Deletion Matching**:
   - `modelStore.delete(name)` matches models by:
     - Full internal name (`models/...`)
     - Short stripped name (without `models/`)
     - `externalModelName`
     - `displayName`
   - Cleans fallback model chains matching any of these aliases.
3. **Synchronous Dynamic Model Invalidation (`syncLanguageServerAndWindows`)**:
   - `storage:delete-custom-model` and `storage:save-custom-model` now invoke `syncLanguageServerAndWindows(getLanguageServerPort)`.
   - Forces Language Server `GetAvailableModels{forceRefresh: true}` to re-query the proxy.
   - Immediately queries fresh `GetUserStatus`.
   - Directly injects into React Fiber (`__reactFiber$`, `__reactContainer$`, `__reactInternalInstance$`) and dispatches `userStatus/setUserStatus` to all windows.
   - Invalidates `customModelsCache.ts = 0` in all window contexts.
4. **Data Store Migration**:
   - Migrated all existing models in `~/.gemini/antigravity/custom_models.json` to clean `apiUrl: "https://ai.odirect.app/v1/"`.
5. **Patcher Verification**:
   - Repackaged and deployed to `/opt/Antigravity-x64/resources/app.asar` with `./manage-antigravity.sh patch-models --force`.
   - Confirmed byte-level parity between `dist/modelPatch/` in `app.asar` and `vendor/antigravity-model-proxy/dist/`.
