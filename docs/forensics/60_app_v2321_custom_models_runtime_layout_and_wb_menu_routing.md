# Forensics Report: Antigravity App v2.32.1 Custom Models Spread Layout & Window Bounds Dispatch

## Incident Summary
Following the release of Antigravity App `v2.32.1` and IDE `v2.7.0`, two distinct functional regressions surfaced during `manage-antigravity.sh update-repo` and `Smart Update All`:
1. **Custom Models Patcher Runtime Abort (`UNSUPPORTED_RUNTIME`):**
   `deploy.mjs` aborted with:
   ```text
   UNSUPPORTED_RUNTIME: dist/languageServer.js: spread arguments are not a recognized startup layout. No application files changed.
   [ERROR] Failed to apply in-app custom models patch via deploy.mjs.
   ```
2. **Instance Configuration Menu Dispatch Failure (`wb` / `WB`):**
   Entering `wb` or `WB` inside the per-instance configuration menu (`configure_unified.py`) looped back to the prompt without triggering `patch_window_bounds.sh`.
3. **Downgrade Test Flake (`test_downgrade.py`):**
   `test_resolver_cli_list_and_resolve` failed assertion because Google published `2.32.1`, replacing `2.31.0` as the latest head release.

---

## Root Cause Analysis

### 1. App v2.32.1 Language Server Arguments Spread Layout
In Antigravity App `v2.32.1`, upstream refactored the language server argument construction:
- Upstream extracted standard CLI flags (`--api_server_url`, `--cloud_code_endpoint`) from `dist/languageServer.js` into a dedicated helper `dist/lsDefaults.js` (`baseLsArgs(opts)`).
- In `dist/languageServer.js`, `const args = [ ... ]` was converted to use the spread operator:
  ```javascript
  const args = [
      ...(0, lsDefaults_1.baseLsArgs)({ ... }),
      '--enable_sidecars',
  ];
  ```
- `vendor/antigravity-model-proxy/scripts/runtime-patch.mjs` strictly enforced literal array elements and threw `UNSUPPORTED_RUNTIME` whenever `elements.some(ts.isSpreadElement)` evaluated to true. Furthermore, searching for AST string literals `'--api_server_url'` and `'--cloud_code_endpoint'` in `fn.body` failed because they now resided in `dist/lsDefaults.js`.

### 2. Window Bounds Patcher Missing Regex & Menu Handler
- In `src/antigravity_suite/detect/configure_unified.py`, the token `"WB"` was rendered in the menu header (`configure_unified_menu.py`) but was missing from the routing `in [...]` checks in lines 82 and 90.
- In `bin/lib/patch/patch_window_bounds.js`, the search regex required `const syncHubViewBounds = () =>` indented by 4 spaces. App `v2.32.1` introduced `let syncHubViewBounds;` at function scope and assigned `syncHubViewBounds = () => { ... }` with 8 spaces indentation and optional chaining `curtainView?.setBounds(...)`.

---

## Resolution & Implementation

### 1. Custom Models AST Patcher Modernization (`runtime-patch.mjs`)
- Detected `hasSpread = elements.some(ts.isSpreadElement)`.
- When spread elements are detected:
  - Injected an in-place array updater right after `const args = [ ... ]` that traverses `args` to set `--api_server_url` and `--cloud_code_endpoint` to `${LOCAL_URL}` and appends `--inference_api_server_url`.
  - Injected module-level property overrides for `lsDefaults_1.LS_API_SERVER_URL` and `lsDefaults_1.LS_CLOUD_CODE_ENDPOINT` at the top of `startLanguageServer`.
  - Preserved backward compatibility for older versions retaining the literal AST replacement path.

### 2. Flexible Window Bounds Patcher & Reversible Unpatch (`patch_window_bounds.js`)
- Updated `ORIG_SYNC_FLEX_RE` to `/([ \t]*)(?:const\s+)?syncHubViewBounds\s*=\s*\(\)\s*=>\s*\{[\s\S]*?baseWin\.on\(['"]resize['"],\s*syncHubViewBounds\);/`.
- Embedded pristine original code within `/* WINDOW_BOUNDS_ORIG_START */` and `/* WINDOW_BOUNDS_ORIG_END */` blocks to guarantee 100% byte-for-byte exact restoration on `--unpatch`.
- Handled optional chaining `curtainView?.setBounds?.(bounds)` and variable declaration scoping (`decl = hasConst ? 'const ...' : '...'`).
- Updated `CLEAN_LINE_RE` to match dynamic indentation for `win.off?.('resize', syncHubViewBounds);`.

### 3. Unified Instance Configuration Menu Routing (`configure_unified.py`)
- Added `"WB"`, `"WINDOW"`, `"WINDOW-BOUNDS"`, `"PATCH-WINDOW"` to the allowed dispatch arrays in both clone and non-clone instances.

### 4. Dynamic Downgrade Release Assertion (`test_downgrade.py`)
- Relaxed exact head version check `2.31.0|` to assert prefix `2.` and presence of `2.31.0|` anywhere in the discovered releases stream.

---

## Verification & Proof
- **JS Integration Tests:** 5/5 passed cleanly (`test_eligibility_normalization.js`, `test_argon_ua_resilience.js`, `test_router_health_and_failover.js`, `test_router_quota_routing.js`, `test_subagent_account_allocator.js`).
- **Python Unit Tests:** 261/261 passed cleanly (`python3 -m unittest discover -s tests -p "test_*.py"`).
- **Live Patch Application:** `bash bin/manage-antigravity.sh patch-all app --app-dir /opt/antigravity2` successfully applied all 6 patches (Custom Models, RTL, Selector, Forking, Open in IDE, Window Bounds) without warnings.
