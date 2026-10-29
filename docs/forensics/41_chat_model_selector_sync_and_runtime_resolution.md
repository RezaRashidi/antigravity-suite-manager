# Case 41: Chat Model Selector Refresh Failure, Language Server Sync, and Runtime Path Resolution

## 1. Executive Summary
After configuring multiple custom models under a gateway (e.g. AIGateway), users noticed that newly added models were saved in Settings but did not appear in the Antigravity Chat UI Model Selector dropdown. The dropdown only displayed the initial model ("DEMO-MODEL"), failing to reflect newly imported models (`cx/gpt-6-luna`, `cx/gpt-5.6-terra`, `cx/gpt-5.6-luna`).

This forensic analysis identifies the root causes across process boundaries (Electron Main, Preload Renderer, and Go Language Server) and details the fix applied to `customIpc.js` and `customPreload.js`.

---

## 2. Root Cause Analysis

### 2.1 Multi-Tier Split Architecture
Antigravity executes across three communicating processes:
1. **Renderer (Chat UI / Settings WebContents)**: Single-page React application hosted by the Go Language Server. Calls `GetAvailableModels` via Connect-RPC on startup and caches the returned model list in Redux client state.
2. **Go Language Server (`language_server`)**: Running on an ephemeral HTTPS port (`--https_server_port 0`). It caches available models in Go memory and periodically (every 5 minutes) polls the proxy endpoint `/v1internal:fetchAvailableModels`.
3. **Electron Main Process & Proxy (`localhost:50999`)**: Reads `~/.gemini/antigravity/custom_models.json`, merges custom models into `/v1internal:fetchAvailableModels`, and handles custom model streaming completions.

### 2.2 Stale React State & 5-Minute Polling Gap
- When Antigravity first started, `custom_models.json` contained only `demo-model`. The Chat UI queried `GetAvailableModels` on boot and loaded only `demo-model`.
- When the user added 4 new models in Settings, they were written to disk. However:
  1. The Language Server only queries `/v1internal:fetchAvailableModels` every 5 minutes.
  2. The Chat UI's React dropdown **never polls** `GetAvailableModels` after mounting.
  3. Consequently, newly added models remained invisible until both the Language Server refreshed its catalog and the Chat UI reloaded.

### 2.3 Broken IPC Sync Handler (`storage:sync-models`)
To solve the 5-minute delay, an IPC trigger (`storage:sync-models`) was previously registered in `customIpc.js` to invoke `languageServer.restartLanguageServer()` and reload windows. However, two bugs prevented it from working:
1. **Relative Path Deficit**: `customIpc.js` was packaged into `dist/modelPatch/customIpc.js`. Calling `require('./languageServer')` looked for `dist/modelPatch/languageServer.js` (non-existent) rather than `dist/languageServer.js` (`../languageServer`), throwing `MODULE_NOT_FOUND` silently in the main process.
2. **Port Mutation Stagnation**: When the Language Server restarts with `--https_server_port 0`, the OS assigns a new ephemeral port. Simply calling `win.webContents.reload()` on the old URL caused connection failure (`ERR_CONNECTION_REFUSED`). The window must be reloaded with `newPort` using `win.loadURL(newUrl)`.

### 2.4 Missing Automatic UI Sync Trigger
In `customPreload.js`, `modelsChanged()` previously rendered a static text prompt:
`Changes saved. Click "Sync to Chat" or press F5 to update Chat model selector.`
Because this was non-interactive and users usually navigated straight back to the Chat view without clicking the distant toolbar button, no sync was dispatched.

---

## 3. Resolution & Architectural Design

### 3.1 Hardened `storage:sync-models` Handler (`customIpc.js`)
Updated the IPC channel in `vendor/antigravity-model-proxy/dist/customIpc.js`:
- Uses relative path fallback `require('../languageServer') || require('./languageServer')`.
- Awaits `ls.restartLanguageServer()`.
- Retrieves `newPort = ls.getLsPort()`.
- Updates the URL of all active windows with `newPort` before reloading:
  ```javascript
  const curUrl = win.webContents.getURL();
  if (newPort && curUrl && curUrl.includes('127.0.0.1')) {
      const parsed = new URL(curUrl);
      parsed.port = String(newPort);
      await win.loadURL(parsed.toString());
  } else {
      win.webContents.reload();
  }
  ```

### 3.2 Actionable Inline Sync Button in Status Banner (`customPreload.js`)
In `modelsChanged()`, dynamically injected a clickable, high-visibility `🔄 Sync to Chat now` button directly inside the status notification element (`#agy-main-status`):
- Provides instant, one-click synchronization right at the point of action.
- Displays live feedback (`Syncing…` -> clean reload).
- Updated gateway auto-import and discovery callbacks to explicitly direct users to sync.

---

## 4. Verification & Validation
1. **Runtime Verification**:
   - Inspected `language_server` response on live port via curl. Verified `response.models` and `agentModelSorts` contains all 4 models:
     `custom-demo-model`, `custom-cx-gpt-6-luna`, `custom-cx-gpt-5-6-terra`, `custom-cx-gpt-5-6-luna`.
2. **Asar Verification**:
   - Re-packed and verified `app.asar` via `./manage-antigravity.sh patch-models --force`.
   - Confirmed coexistence of F5 reload, RTL, multi-account selector, and custom models patches.
3. **Test Suite**:
   - All 214 tests passing cleanly via `pytest`.
   - File length rule (`<= 100 lines` for all `.py` and `.sh` files) verified.
