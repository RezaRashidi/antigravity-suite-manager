# Issue 16: F5 Backend Reload Failure (Stale Handler, Empty Try Block, and Patch Skip Guard)

### Symptoms
* Pressing `F5` in the Antigravity Desktop App displayed the `Syncing...` toast, but the backend Go Language Server process was never restarted, and changes to the SQLite database or conversation summaries on disk were not refreshed.
* Running `manage-antigravity.sh f5` or `antigravity-f5-patch.js` repeatedly reported success (`[Patch] dist/utils.js already patched`), yet the reload behavior remained permanently broken.

### Root Cause
1. **Empty Try Block in `app.asar` (`dist/utils.js`)**:
   Decompiling `/opt/Antigravity-x64/resources/app.asar` revealed that `onRestartRequested` contained an empty `try` block:
   ```javascript
   const languageServer = require('./languageServer');
   if (languageServer && languageServer.restartLanguageServer) {
       try {
           // Completely empty: restartLanguageServer was never called!
       } catch (_) {}
   }
   if (win && !win.isDestroyed() && win.webContents) {
       setTimeout(() => {
           try {
               if (win && !win.isDestroyed() && win.webContents) {
                   win.webContents.reload();
               }
           } catch (_) {}
       }, 300);
   }
   ```
   Only the frontend webview page reloaded; the Go Language Server (`language_server`) was never restarted.

2. **Early-Exit Guard Preventing Re-Patching**:
   In `bin/lib/patch/patch_utils_reload.js`, the patcher checked:
   ```javascript
   if (code.includes('onRestartRequested:')) return code;
   ```
   Because `onRestartRequested:` was already present in `app.asar` (holding the broken empty block), the patcher immediately exited without making changes. Re-running the patch tool had zero effect.

3. **Window Reload Race Condition**:
   In `dist/languageServer.js`, `restartLanguageServer()` triggers `onPortChanged(newPort)`, which calls `win.loadURL(newUrl)` for all windows on the newly assigned ephemeral port. Calling `win.webContents.reload()` unconditionally right after `restartLanguageServer()` aborted the in-flight `loadURL` navigation or reloaded the old dead port.

### Solution Applied
1. **Dynamic Cleanup in Patcher**:
   Updated [bin/lib/patch/patch_utils_reload.js](src/../bin/lib/patch/patch_utils_reload.js) to strip any existing `onRestartRequested` block before injecting the fresh implementation:
   ```javascript
   if (code.includes('onRestartRequested:')) {
       code = code.replace(/\s*onRestartRequested:\s*async\s*\(\)\s*=>\s*\{[\s\S]*?\n\s*\},(?=\s*\n\s*\}\);)/, '');
   }
   ```
2. **Explicit Restart & Fallback Navigation**:
   Updated the injected handler to invoke `await ls.restartLanguageServer()` and set a `restarted = true` guard, preventing conflicting reloads while preserving `win.webContents.reload()` as a fallback if the language server is unavailable:
   ```javascript
   let restarted = false;
   try {
       const ls = require('./languageServer');
       if (ls && typeof ls.restartLanguageServer === 'function') {
           await ls.restartLanguageServer();
           restarted = true;
       }
   } catch (err) {
       console.error('[Keybindings] LanguageServer restart failed:', err);
   }
   if (!restarted && win && !win.isDestroyed() && win.webContents) {
       try { win.webContents.reload(); } catch (_) {}
   }
   ```
3. **App Patch Application & Verification**:
   Applied the patch cleanly to `/opt/Antigravity-x64/resources/app.asar` and verified that `await ls.restartLanguageServer()` is present and active.
4. **Automated Regression Test**:
   Added `test_patch_utils_reload_replaces_stale_handler` in [tests/test_fixes_validation.py](tests/test_fixes_validation.py). All 120 tests passing.

---
