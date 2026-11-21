# Issue 64: Antigravity App v2.34.0 `loadURL` Refactor & Custom Models Pristine Backup Corruption

## Symptom
After upgrading Antigravity App to `v2.34.0`, running `[AP] Apply All Patches` failed on three patches:
1. `[1/7] In-App Custom Models UI`: `UNSUPPORTED_RUNTIME: dist/main.js: already patched; use the verified original archive for this version.`
2. `[2/7] RTL Typography`: `✖ Injection failed. Injection anchor not found. The app version might be unsupported.`
3. `[7/7] Prompt Input Typing Performance`: `Error: Could not find dom-ready or loadURL hook in dist/utils.js`

## Root Cause (Triggered by New Antigravity App v2.34.0)
1. **Upstream `dist/utils.js` refactor in `v2.34.0`:**
   Antigravity App `v2.34.0` moved window navigation into `async function invokeWindowLoadUrl(win, url)` and replaced `void win.loadURL(url);` with `await win.loadURL(url);`.
   - `antigravity-rtl` (`v1.4.1`) strictly looks for `ANCHOR = 'void win.loadURL(url);'` and failed with `Injection anchor not found`.
   - `patch_typing_perf.js` checked only `win.webContents.on('dom-ready', () => {` and `void win.loadURL(url);`.
2. **Pristine backup overwrite in `restore_pristine_models_base`:**
   In `bin/lib/sh/patch_models_helpers.sh`, `detect_active_patches` checked only the 6 post-model patches and ignored `antigravity-model-patch`. When `app.asar` had only `antigravity-model-patch` applied, `has_active` evaluated to `false`, causing `restore_pristine_models_base` to overwrite `app.asar.orig` with the already-patched `app.asar` and delete `.antigravity-model-patch/`. `deploy.mjs` then rejected the already-patched runtime.

## Resolution
1. **`bin/lib/patch/patch_typing_perf.js`:** Added support for `await win.loadURL(url);`, injecting the `dom-ready` / `did-finish-load` listener immediately before the `await`.
2. **`bin/lib/patch/patch_rtl_v234_shim.js` & `bin/lib/sh/patch_rtl.sh`:** Added `--prepare` / `--finalize` compatibility shim for App `>= v2.34.0` that temporarily exposes `void win.loadURL(url);` for `antigravity-rtl` and restores `await win.loadURL(url);` after `dom-ready` registration.
3. **`bin/lib/sh/patch_models_helpers.sh` & `bin/lib/sh/patch_models.sh`:** Guarded `restore_pristine_models_base` so a model-patched `app.asar` never overwrites `app.asar.orig` or deletes `.antigravity-model-patch/`, and skipped re-injection gracefully when `antigravity-model-patch` is already present without a pristine backup.

## Verification
- `bash -n` on `patch_models_helpers.sh`, `patch_models.sh`, `patch_rtl.sh` and `node -c` on `patch_typing_perf.js`, `patch_rtl_v234_shim.js` passed.
- End-to-end test on an isolated copy of `v2.34.0` `app.asar` verified RTL injection (`PREPARED` -> `antigravity-rtl` -> `FINALIZED`) and `patch_typing_perf.js` (both stacked on RTL and standalone).
