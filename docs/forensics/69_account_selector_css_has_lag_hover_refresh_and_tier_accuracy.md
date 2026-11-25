# Forensic Analysis 69: Account Selector `:has()` Typing Lag, On-Hover Single-Account Refresh & Tier/Verification Reporting

## 1. Problem Statement
Users reported five interrelated regressions in the multi-account selector patch (confirmed absent on unpatched installations):
1. Severe typing stutter and buffered character bursts in the bottom prompt input bar.
2. Stale standalone `typing_perf` patch cluttering menus/CLI instead of fixing the root cause in the selector itself.
3. Unwanted background/modal-open network refreshes causing UI hangs when opening the account dropdown.
4. Misclassification of `Free Pro` accounts as `PAID PRO`.
5. Missing verification links, logged-out indicators, and explicit refresh/error feedback in the selector UI.

## 2. Root Cause Analysis

### A. Global CSS `:has()` Selectors Triggering Keystroke Reflows
In `bin/lib/patch/ui/styles.css`, five global rules used `div:has(button[title*="Reset"])` and `div.shrink-0:has(...)` to hide the developer footer. In Chromium/Blink, global `div:has(...)` selectors force subtree style invalidation sweeps across `div` ancestors on DOM mutations (including prompt typing), causing periodic main-thread stalls.

### B. Redundant Injections, Unbounded Footer Observer & Pill DOM Rebuilds
- `bin/lib/patch/ui/mount.js` and `bin/lib/patch/ui/flyout.js` lacked idempotency guards, allowing duplicate initialization across `dom-ready` and `did-finish-load` (`patch_multi_account_ui_inject.js` also re-executed `insertCSS` without URL deduplication).
- `footerMo` in `mount.js` stayed attached indefinitely on production builds lacking a `"Reset State"` button.
- `render()` in `bin/lib/patch/multi_account_ui.js` rebuilt `pill.innerHTML` even when account/cascade state was unchanged, and `MutationObserver` / `setInterval` / `fetchState` polled every 30s in the background.

### C. Modal-Open Blocking Refresh & Hover Storm
- Triggering `/api/multi-account/state?refresh=1&wait=1` for all accounts synchronously on dropdown open (or repeatedly on `hover` for unhealthy accounts with empty `quotas`) blocked waiting up to 4.5s per wave and serialized OAuth refreshes for valid tokens.
- On 403 responses already containing explicit `no_license` or `verify_required` payloads, `telemetry.js` needlessly ran `loadCodeAssist` warmup + retry cycles.

### D. `Paid Pro` Misclassification via `tagTitle: "New"`
Google began returning `tagTitle: "New"` on `gemini-4-hydrogen-*` across `Free` and `Free Pro` tiers (`23` enabled + `3` disabled upgrade-notice models). Checking `models[k].tagTitle === 'New'` in `telemetry.js` therefore labeled all accounts as `Paid Pro`.

### E. Missing Verify URLs, Revoked Token Detection & Error States
- `classifyHttpError` did not extract `validation_url` / `verification_url` from 403 `details[].metadata` or body URLs.
- `oauth.js` returned stale `currentAccess` even after `invalid_grant`, delaying `LOGGED OUT` state until access token expiration.
- Cached quota fallbacks masked live refresh failures.

## 3. Fixes Implemented

1. **Removed CSS `:has()` & Duplicated Observers (`styles.css`, `mount.js`, `flyout.js`, `patch_multi_account_ui_inject.js`, `multi_account_ui.js`):**
   - Replaced `:has(...)` rules with `.agy-hidden-dev-footer` toggled once by JS; added 8s bounded auto-disconnect on `footerMo`.
   - Added `__antigravityMountInit` / `__antigravityFlyoutInit` guards and `insertCSS` per-URL deduplication.
   - Added `renderSig` diff check to skip no-op `pill.innerHTML` rebuilds, O(1) active-typing bypass (`lastTypingTs`, `isTypingEl`), and removed the 30s background poll.

2. **Retired Redundant `typing_perf` Patch:**
   - Removed `patch_typing_perf.js`, `patch_typing_perf.sh`, `test_typing_perf_patch.py`, and all CLI/menu/Control Center/update hooks.

3. **Instant Modal Open & On-Hover Single-Account Refresh (`multi_account_router.js`, `api.js`, `multi_account_ui.js`, `patch_multi_account_ipc.js`):**
   - Dropdown opens in 0ms purely from local cache; no background or boot-time network refreshes occur.
   - Moving onto an account row (or clicking `›`) triggers a deduplicated single-account refresh (`?refresh=1&wait=1&email=...`, 15s per-account cooldown, 6s `AbortController`), updating row badges and flyout live without blocking UI hover.
   - Added token expiry fast-path (>5m TTL) in `oauth.js`, skipped redundant warmup when 403 already classifies cleanly, and ran `fetchLanguageServerTelemetry` in parallel with direct quota checks.

4. **Accurate `Paid Pro` vs `Free Pro` vs `Free` Classification (`telemetry.js`):**
   - Added `classifyAccountTier(models)`: filters `-disabled` upgrade notices, detects `tagTitle: "Paid Pro"` / `"not included with your current plan"`, and grants `Paid Pro` only when exclusive enabled models (`5-5`, enabled `neon`/`carbon`) exist without disabled notices.

5. **Verification Links, Logged-Out & Refresh Error UI (`accounts.js`, `telemetry.js`, `multi_account_router.js`, `flyout.js`, `multi_account_ui.js`):**
   - Extracts `verify_url` and renders clickable **Verify Account ↗** + **Copy Link** controls in the flyout.
   - Detects `invalid_grant` immediately as `LOGGED OUT`, plus `NO LIC`, `LIMIT`, and `ERR` / `Refresh Failed` / `Not Refreshed (Cached)` banners.

## 4. Verification
- All 9 Node.js test suites (including extended `tests/test_typing_performance_isolation.js`) and all 261 Python tests passed.
- Live benchmark showed full 7-account refresh dropped from `4526ms` to `1023ms` with accurate separation across `Paid Pro` (37 models), `Free Pro` (23 models), and `No License`.
- Re-deployed multi-account selector cleanly to `/opt/antigravity2` (App) and `/opt/antigravity` (IDE).
