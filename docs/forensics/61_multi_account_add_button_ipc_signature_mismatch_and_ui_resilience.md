# Forensic Analysis 60: Multi-Account "+ Add Account" Button Silent Failure & IPC Signature Mismatch

## 1. Problem Statement
In Antigravity App `v2.32.1`, clicking the `+ Add Account` button in the prompt-bar multi-account selector dropdown produced zero user feedback and failed to initiate the Google OAuth sign-in flow.

## 2. Root Cause Analysis

### A. IPC Registration Function Signature Mismatch
In `bin/lib/patch/patch_multi_account_ipc.js`, the patcher injected IPC handlers by performing an exact literal string search:
```javascript
code.replace('function registerIpcHandlers(storageManager) {', ...)
```
Upstream Antigravity App `v2.32.1` updated the function signature in `dist/ipcHandlers.js` to:
```javascript
function registerIpcHandlers(storageManager, deps = {}) {
```
Because the literal string did not match, `snippets` containing `multi-account:start-login`, `multi-account:get-state`, and associated handlers were never injected into `dist/ipcHandlers.js`.

### B. Uncaught Exception in UI Click Handler
In `bin/lib/patch/multi_account_ui.js`:
```javascript
document.getElementById("agy-acc-add")?.addEventListener("click", async (e) => {
    e.stopPropagation();
    if (window.antigravityMultiAccount?.startLogin) await window.antigravityMultiAccount.startLogin();
    else {
        // Fallback HTTP POST /api/multi-account/login
    }
});
```
`preload.js` correctly exposed `window.antigravityMultiAccount.startLogin` via Electron `ipcRenderer.invoke('multi-account:start-login')`. However, because the handler was absent in `ipcMain`, `ipcRenderer.invoke` threw:
`Error: No handler registered for 'multi-account:start-login'`
Because there was no `try/catch` wrapping `await window.antigravityMultiAccount.startLogin()`, the promise rejection crashed the event listener silently before reaching the HTTP fallback or displaying an alert.

### C. Missing X11 Environment Propagation in Child Processes
Detached spawn calls in `patch_multi_account_ipc.js`, `router/api.js`, and `antigravity-multi-account-ide.js` did not explicitly pass `DISPLAY` and `XAUTHORITY`. When triggered from certain desktop or subagent environments, `webbrowser.open(url)` failed silently due to absent display sockets.

### D. Stale PID Lock File
A stale lock file at `~/.config/antigravity/accounts/login.pid` from previously terminated attempts could block subsequent authentication flow attempts.

## 3. Engineering Fixes

1. **Flexible IPC Regex Matching & Marker Blocks:**
   Updated `bin/lib/patch/patch_multi_account_ipc.js` to match with regex `/function registerIpcHandlers\s*\([^)]*\)\s*\{/`, wrapping the injected handlers with clear `/* AGY_MULTI_ACCOUNT_IPC_START */` and `/* AGY_MULTI_ACCOUNT_IPC_END */` demarcation comments for robust, idempotent patching and clean unpatching.

2. **Resilient UI Flow with Immediate Feedback:**
   Updated `bin/lib/patch/multi_account_ui.js` to immediately display a `toast("Opening browser sign-in...")`, wrap `startLogin()` in a `try/catch` block, fall back to the router HTTP POST `/api/multi-account/login` route if IPC fails, and present an alert with manual CLI instructions if both paths fail.

3. **Guaranteed X11 Display & Authority Propagation:**
   Ensured `DISPLAY: process.env.DISPLAY || ':0'` and `XAUTHORITY: process.env.XAUTHORITY || require('path').join(rh, '.Xauthority')` are passed to spawned Python processes across `patch_multi_account_ipc.js`, `router/api.js`, and `antigravity-multi-account-ide.js`.

4. **Stale PID Lock Cleanup:**
   Removed stale `login.pid` and verified `lock.py` process-death recovery.

5. **Automated Regression Test Suite:**
   Added `tests/test_multi_account_ipc_patch.js` covering both modern `v2.32+` and legacy function signatures, unpatch integrity, and HTTP `/api/multi-account/login` endpoint dispatch.

## 4. Verification & Validation
- Node.js test suite: 6/6 tests passed.
- Python unittest suite: 261/261 tests passed.
- Verified `/opt/antigravity2/resources/app.asar` has `multi-account:start-login` and marker blocks present.
- Verified `/opt/antigravity/resources/app/out/antigravity-multi-account-ide.js` contains proper `DISPLAY` env handling.
- Verified `curl -X POST http://127.0.0.1:41999/api/multi-account/login` returns `{"ok":true}` and spawns login process.
