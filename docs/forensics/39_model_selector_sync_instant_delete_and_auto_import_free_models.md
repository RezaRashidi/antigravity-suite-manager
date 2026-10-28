# Case 39: Model Selector Sync, Instant Deletion, and Auto-Import Free Models

## 1. Executive Summary
Following the implementation of in-app Custom Models settings and multi-provider gateway support (Cases 36–38), user testing identified four usability bottlenecks:
1. **Model Selector Stagnation**: Adding, editing, deleting, or toggling models in Settings did not immediately reflect in Antigravity's chat model selector dropdown.
2. **Deletion Friction**: Deleting a model presented an intrusive browser confirmation prompt (`window.confirm`), slowing down batch cleanup.
3. **Discover Models Redundancy**: Clicking "Discover models" opened a generic modal displaying redundant gateway configuration fields (URL, API key) requiring manual fetch invocation instead of directly querying the gateway.
4. **Missing Free Models Auto-Import**: Users required a one-click auto-import mechanism to detect and activate all models with the keyword `free` without manual catalog selection.

---

## 2. Root Cause Analysis

### 2.1 Model Selector Synchronization Lifecycle
Antigravity operates a split architecture:
- Electron Main process launches a Go Language Server (`language_server`) listening on an ephemeral port.
- The Language Server periodically (every 5 minutes) queries `--api_server_url` for `/v1internal:fetchAvailableModels`.
- Our proxy intercepts this endpoint and merges custom models.
- When the chat UI mounts, it queries `language_server` via Connect-RPC and stores available models in Redux/React client-side state.
- In Settings, `modelsChanged()` previously only updated the Settings DOM (`#agy-custom-models-content`) and had no IPC channel to notify the Language Server or reload the chat window. Consequently, modified models were only fetched after a 5-minute wait or complete application restart.

### 2.2 Delete Confirmation Modal
In `customPreload.js:690`, model deletion was wrapped with:
```javascript
if (!window.confirm(`Delete “${model.displayName || model.name}”?`)) return;
```
This modal interrupted workflow and was undesired for rapid model management.

### 2.3 Discover Models View Configuration Bloat
`openModelModal(first, 'discover')` was previously reusing the comprehensive model creation form, exposing raw API URL and API key fields and requiring the user to locate and click "Fetch provider models". The gateway's credentials are already configured at the card level.

---

## 3. Implementation Details

### 3.1 Instant Deletion
Removed `window.confirm` entirely from the model row deletion handler in `customPreload.js`:
```javascript
button('Delete', async () => {
    requireSuccess(await storageAPI.deleteCustomModel(model.name));
    await modelsChanged();
}, rowStatus)
```

### 3.2 Streamlined `openDiscoverGatewayModels`
Created a specialized modal dedicated exclusively to gateway model discovery:
- Omits gateway configuration inputs (URL, API token, API format).
- Automatically invokes `storageAPI.discoverModels(gateway)` upon opening.
- Displays search filter, live count, "Select All", "Deselect All", and checkboxes for each discovered model.
- Includes a collapsible manual model ID section for custom endpoints.

### 3.3 Auto-Import Free Models Button (`وارد کردن خودکار مدل‌های free`)
Added a dedicated button to each gateway card:
- Automatically queries `storageAPI.discoverModels(gateway)`.
- Filters catalog items with `/free/i.test(...)` across `id`, `name`, and `displayName`.
- Batch-inserts or re-enables matching models directly with `enabled: true`.
- Updates model list without opening discovery dialogs.

### 3.4 Language Server Sync & "Sync to Chat"
1. **IPC Channel (`storage:sync-models`)**:
   In `customIpc.js`, added handler invoking `languageServer.restartLanguageServer()` and window reloads to flush React client caches.
2. **Toolbar Sync Trigger**:
   Added a primary button `🔄 Sync to Chat` in the Settings toolbar alongside visual status feedback in `modelsChanged()`.
3. **Interceptor Hardening**:
   In `desktop.js`, decoupled `LanguageServerService/GetAvailableModels` redirection from strict ephemeral port equality, ensuring gRPC requests always route through loopback proxy handlers.

---

## 4. Verification & Validation
- **Unit Tests**: 214 tests passing in `pytest` (including `test_patch_models.py` validation of new methods and absence of `window.confirm`).
- **File Length Bounds**: All `.py` and `.sh` files strictly maintain `<= 100 lines`.
- **Multi-Patch Coexistence**: Verified simultaneous application of Model Settings UI, RTL patch, F5 keybindings, and multi-account selector in `app.asar`.
