# Forensic Analysis Case 46: Multi-Account Proxy Chaining & Language Server Quota Cache Invalidation

## 1. Executive Summary
Following the deployment of the Custom Models local proxy (`vendor/antigravity-model-proxy/dist/proxy.js`) listening on port `50999`, users experienced an issue where switching active Google accounts in the UI Account Selector failed to update the quota in the Model Selector flyout. In long conversations (such as `5a9cebeb-9582-4fa9-97c0-4b5d2d885fb9`), the Primary account exhausted its upstream quota (429 RESOURCE_EXHAUSTED), locking up context summarization and preventing subagent execution despite other configured accounts having ample quota (>90%).

Investigation revealed a dual root cause:
1. **Broken Proxy Chaining**: The Custom Models proxy forwarded Google Cloud Code upstream requests (`/v1internal:*`) directly to `daily-cloudcode-pa.googleapis.com` using the primary account token, completely bypassing the Suite Manager's MultiAccountRouter on port `41999`.
2. **Stale In-Memory Quota Cache**: The Go `language_server` binary caches upstream quota responses in `retrieveUserQuotaSummaryCache`. Without an explicit Connect-RPC invalidation signal (`{"forceRefresh": true}`), the Language Server never queried the proxy even after an account switch.

Both issues were resolved by establishing a reliable 2-stage proxy bridge and triggering Connect-RPC cache invalidation on account binding.

---

## 2. Architecture & Root Cause Analysis

### 2.1 The 2-Stage Proxy Bridge Failure
Antigravity executes with `--cloud_code_endpoint http://localhost:50999`. Under the previous implementation:
```
Language Server ---> Port 50999 (Custom Models Proxy) ---> daily-cloudcode-pa.googleapis.com (Direct)
                         |
                 (Bypassed Port 41999 MultiAccountRouter entirely!)
```
Because Port 41999 was bypassed:
- Token swapping never occurred for Language Server calls.
- `cascadeId` and conversation account bindings were ignored.
- Traffic logging in `~/.config/antigravity/accounts/traffic.log` ceased recording Language Server calls.

### 2.2 In-Memory Connect-RPC Cache
The Language Server implements Connect-RPC endpoint:
`/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary`
Even if upstream credentials changed, the Go binary returned cached quota figures until internal TTL expiration, keeping the UI Model Selector flyout in a stale or exhausted state.

---

## 3. Resolution & Implementation

### 3.1 Chained Forwarding in `vendor/antigravity-model-proxy/dist/proxy.js`
- Defined `MULTI_ACCOUNT_PORT = 41999`.
- Implemented `isMultiAccountAvailable()` checking loopback HTTP `/healthz` on port 41999.
- Updated `proxyToGoogle()` and `/v1internal:fetchAvailableModels`:
  - When target is Cloud Code PA (`v1internal` or `daily-cloudcode`), requests are piped to `http://127.0.0.1:41999` using Node's `http.request`.
  - Added seamless fallback: If port 41999 returns `ECONNREFUSED` or is unavailable, requests automatically fall back to `https://daily-cloudcode-pa.googleapis.com`.

### 3.2 Cache Invalidation in `bin/lib/patch/router/telemetry.js` & `api.js`
- Implemented `forceRefreshLanguageServerQuota()`:
  - Scans `/proc` to locate active `language_server` processes.
  - Extracts the active `--csrf_token`.
  - Discovers the listening Connect-RPC HTTPS port (e.g. 37443).
  - Sends a `POST` request to `/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary` with payload `{"forceRefresh": true}` and header `x-codeium-csrf-token`.
- Wired `forceRefreshLanguageServerQuota()` into `/api/multi-account/bind` and `/api/multi-account/set-active` in `router/api.js`.

### 3.3 Dynamic Model Selector Refresh in `bin/lib/patch/multi_account_ui.js`
- Invoked `window.__antigravityRefreshModels?.()` in the account switch click handler so the UI immediately triggers a re-fetch of available models and quotas.

---

## 4. Verification & Status
- Connect-RPC test confirmed: Port `37443` responded with `status: 200` and updated quota payload.
- All 219 regression tests passed (`Ran 219 tests in 14.010s OK`).
- Full compatibility with RTL, F5 reload, custom models, and multi-account rotation maintained.
