# Forensic Analysis Case 57: Account Health Quarantine, HTTP 403/401 Failover & Bounded GZIP Classification

## Executive Summary

Users repeatedly encountered UI-blocking errors `"Please verify your account to continue using Antigravity. Learn more"` and silent `"NO LICENSE"` failures when chatting or opening new cascades, even when multiple healthy Google accounts were signed in.

Forensic inspection of router traffic and `language_server` logs proved two interacting root causes:
1. Unverified (`verify_required`) and unlicensed (`no_license`) accounts were returned verbatim from upstream HTTP 403 responses without quarantining the bad account or failing over to healthy accounts.
2. When `/api/multi-account/bind`, `/api/multi-account/set-active`, `/api/multi-account/switch`, `subagent_allocator.js`, or telemetry quota checks ran, unhealthy accounts remained selectable and stale health metadata could drift or loop indefinitely.

---

## Root Cause Findings from Production Logs

- `traffic.log` & `language_server.log` confirmed `reza93ai20224@gmail.com` received upstream `HTTP 403 PERMISSION_DENIED: Verify your account to continue.` (`verify_required`).
- `aisummerreza@gmail.com` received upstream `HTTP 403` (`You do not have a valid license`, `no_license`).
- Meanwhile, 4 other accounts (`rezalast4m@gmail.com`, `aiyearreza@gmail.com`, `rezaseptem93@gmail.com`, `rezastuai@gmail.com`) responded `HTTP 200` with full quota buckets.
- Because the previous router build (`2026-11-11`) had no health quarantine or HTTP 403 automatic failover in `server.js`, active sessions bound to `reza93ai20224@gmail.com` propagated raw `403` verification banners straight to the desktop client.

---

## Implemented Architecture & Fixes

### 1. Account Health & Quarantine State Machine (`bin/lib/patch/router/accounts.js`)
- **`classifyHttpError(statusCode, bodyStr)`**:
  - `verify your account` -> `verify_required` (`persist: true`)
  - `valid license|SUBSCRIPTION_REQUIRED|UNSUPPORTED_CLIENT` -> `no_license` (`persist: true`)
  - `401` or `UNAUTHENTICATED|invalid_grant` -> `auth_failed` (`persist: true`)
  - generic `403` -> `forbidden_transient` (`persist: false`, 60s `TRANSIENT_COOLDOWN_MS`)
- **`markAccountUnhealthy` & `clearAccountUnhealthy`**:
  - Tracks in-memory `_unhealthyAccounts` cooldown map (`DEFAULT_UNHEALTHY_COOLDOWN_MS = 30m`, `TRANSIENT_COOLDOWN_MS = 60s`) and optionally persists `license_status`, `license_message`, `unhealthy_at`, `unhealthy_until`, `unhealthy_token_fp`, and `tier` (`Verify Required` / `No License` / `Auth Required`) using atomic temp-rename writes (`writeJsonAtomic`).
  - `clearAccountUnhealthy` restores `license_status = 'ok'` and restores `tier` from `tier_type` when cleaning `Verify Required`, `No License`, or `Auth Required`.
- **`isAccountHealthy` & `pickHealthyFallbackAccount`**:
  - Auto-expires quarantine when `unhealthy_until` passes or when a new refresh token fingerprint (`unhealthy_token_fp !== curFp`) is detected (e.g., after re-login).
  - Ranks healthy fallbacks preferring `license_status === 'ok'`, paid tier, and alphabetical determinism.
- Excluded `subagent_policy.json` explicitly from account discovery loops.

### 2. Bounded Error Classification, GZIP Decompression & SSE Failover (`bin/lib/patch/router/server.js`)
- Buffered HTTP `403`/`401` upstream responses up to a bounded limit and decoded `gzip`/`deflate` cleanly via `decodeUpstreamBuffer` (handling truncated gzip streams safely without corrupting responses or hanging).
- Added up to `MAX_FAILOVER_ATTEMPTS = 6` healthy account re-attempts before surfacing an upstream error; updates active/cascade bindings when failover succeeds.
- Added `res.on('close')` client disconnect cleanup (`!res.writableEnded`) to abort in-flight upstream requests cleanly and release subagent in-flight tracking (`finishInFlight()`).
- Attached `upRes.on('error')` listeners across direct SSE, JSON, and failover response paths to prevent uncaught stream exceptions.

### 3. Telemetry, OAuth, API Guards & Subagent Isolation
- `bin/lib/patch/router/telemetry.js`: Added `timeout` -> `req.destroy()` handlers, `res.on('error')` safety, and strict `PERMISSION_DENIED` / `"error":` JSON checks on HTTP 403 classification; `multi_account_router.js` preserves persisted `tier` when `directFailed` and writes via `writeJsonAtomic`.
- `bin/lib/patch/router/oauth.js`: Clears `auth_failed` state and writes atomically when Google OAuth token refresh succeeds.
- `bin/lib/patch/router/api.js` & `bin/lib/patch/router/bindings.js`: Fixed `getActiveAccountEmail(accountsMap)` Map/Array handling and added health guards to `/api/multi-account/bind`, `/api/multi-account/set-active`, and `/api/multi-account/switch` returning `{ ok: false, skipped: true, unhealthy: true }` for quarantined targets.
- `bin/lib/patch/router/subagent_allocator.js`: Evicts unhealthy subagent leases and filters candidate accounts through `isAccountHealthy`.

### 4. UI Badges, XSS Hardening & ESM Facade (`bin/lib/patch/multi_account_ui.js`, `ui/flyout.js`, `patch_multi_account_ui_inject.js`)
- Added `VERIFY`, `NO LICENSE`, and `AUTH` status badges and warnings in the account quota flyout (`ui/flyout.js`), with `escHtml` escaping for `email` and `planName`.
- Updated `multi_account_ui.js` to inspect `/bind` responses (`skipped && unhealthy`) before displaying `"✓ Switched"` toasts.
- Exposed `isAccountHealthy`, `markAccountUnhealthy`, and `clearAccountUnhealthy` on the ESM facade generated by `patch_multi_account_ui_inject.js`.

---

## Verification

- Added comprehensive regression tests in `tests/test_router_health_failover.js` and expanded `tests/test_eligibility_middleware.js`.
- Verified all 5 JavaScript test suites pass (`exit 0`):
  - `tests/test_eligibility_middleware.js`
  - `tests/test_router_argon_hang_and_ua.js`
  - `tests/test_router_health_failover.js`
  - `tests/test_router_quota_routing.js`
  - `tests/test_subagent_router.js`
- Deployed via `bash bin/manage-antigravity.sh patch-selector` to `/opt/antigravity2/resources/app.asar` and `/opt/antigravity/resources/app/out`.
