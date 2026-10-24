# Forensic Incident Report #35: Core Quota Router Scoping Regression & Multi-Account Model Selector Sync Failure

## 1. Executive Summary & Incident Chronology

### Incident Context
Following a restart of Antigravity by the operator, switching Google accounts in the prompt bar Account Selector failed to update the remaining quota percentages and available model limits displayed in the native Model Selector dropdown:
> "Look, when I change the account in the account selector, in the model selector which shows the quota, the quota doesn't change! On the other system where I developed this, it was ok... Core Quota Router was not fixed after restart. Investigate why this happened and find the bug."

### Forensic Diagnosis
Comprehensive forensic tracing across the Go Language Server (`/opt/antigravity2/resources/bin/language_server`), Electron main process proxy router (`bin/lib/patch/router/server.js`), and traffic logs (`~/.config/antigravity/accounts/traffic.log`) pinpointed two interconnected root causes:
1. **Scoping Regression in `server.js` (Commit `ef48f90`)**:
   Token swapping was scoped strictly to `streamGenerateContent` and `generateContent` via `isGen`. Upstream Language Server quota and model configuration RPCs (`/v1internal:retrieveUserQuotaSummary`, `/v1internal:retrieveUserQuota`, `/v1internal:fetchAvailableModels`, `/v1internal:loadCodeAssist`, `/v1internal:fetchUserInfo`, `/v1internal:listModelConfigs`) were categorized as `ControlPlane` and dispatched with the Primary account's native session token. Consequently, Google Cloud Code returned Primary account quotas regardless of which account was selected.
2. **Conversation Binding & Active State Decoupling in UI (`multi_account_ui.js` & `api.js`)**:
   When switching accounts on an existing conversation (UUID), `multi_account_ui.js` marked `active: isDraft`. Because `isDraft` was `false` for non-draft UUIDs, `api.js` skipped `setActiveAccount(email)` and left `_lastCascadeId` untouched. When Language Server subsequently polled `/v1internal:retrieveUserQuotaSummary` (which carries an empty payload `{}` without `cascadeId`), the router resolved `null` conversation context and fell back to the unchanged primary default.

---

## 2. Root Cause Analysis (RCA)

### Cause A: The `isGen` Scoping Regression (Commit `ef48f90`)
In commit `ef48f90ca9fc4457d766ef067ef4c569057daacc` ("fix(router,detect): scope token swapping strictly to chat generation RPCs"), token swapping was restricted:
```javascript
// Defective logic in server.js
const isGen = req.url && (req.url.includes('streamGenerateContent') || req.url.includes('generateContent'));
let token = null, boundEmail = 'Primary (Native)';
if (isGen) {
    ...
    token = await resolveTokenForCascade(cascadeId);
} else {
    logTraffic(`ControlPlane: [${cascadeId || 'system'}] -> Native LS Session | Path: ${req.url}`);
}

const headers = { ...req.headers, host: UPSTREAM_HOST };
if (isGen && token) headers.authorization = `Bearer ${token}`;
```
- In Antigravity Hub and IDE, the native prompt-bar model selector does not poll the account manager; it queries the local Go Language Server ConnectRPC endpoint (`/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary`).
- In turn, the Language Server periodically polls upstream `--cloud_code_endpoint` (`http://127.0.0.1:41999`) on path `/v1internal:retrieveUserQuotaSummary`.
- Because `isGen` was `false` for quota and model endpoints, `server.js` forwarded every quota request with the **Primary Account's Authorization header**.
- Google Cloud Code returned the Primary account's quota buckets. Language Server cached these responses and returned them to the model selector, causing quota displays to remain static when switching accounts.

### Cause B: `setActiveAccount` Guard in `api.js` & `multi_account_ui.js`
In `api.js`:
```javascript
if (req.url === '/api/multi-account/bind' && req.method === 'POST') {
    const data = JSON.parse(bodyStr);
    if (data.cascadeId && data.email) {
        setBinding(data.cascadeId, data.email, data.model || '');
        if (data.active && (data.cascadeId === '__default__' || data.cascadeId === 'default' || data.cascadeId.startsWith('draft_') || data.cascadeId.startsWith('chat_'))) setActiveAccount(data.email);
    }
}
```
- When an operator clicked an account in the dropdown for an existing conversation, `data.cascadeId` was a UUID (e.g., `7b382c83-e685-4637-84bc-4520cdfcb94c`).
- `data.active` was passed as `false` by `multi_account_ui.js` because `!isDraftId(cascadeId)`.
- As a result, `setActiveAccount(data.email)` was bypassed, leaving `bindings.__active_account` unchanged.
- Furthermore, `_lastCascadeId` in `server.js` was only refreshed when chat text was generated, expiring after 30 seconds (`Date.now() - _lastCascadeTs < 30000`). Once expired, payload-less quota requests (`{}`) could not resolve the conversation ID, falling back to the stale active account.

---

## 3. Surgical Implementation & Remediation

### 1. Expanded Account RPC Recognition in `server.js`
Token resolution was expanded to encompass all account-dependent quota, model, and user configuration endpoints, while preserving untokenized passthrough for true Googler control-plane endpoints (`listExperiments`, `cascadeNuxes`):
```javascript
const isGen = req.url && (req.url.includes('streamGenerateContent') || req.url.includes('generateContent'));
const isAccountRpc = req.url && (
    isGen ||
    req.url.includes('retrieveUserQuota') ||
    req.url.includes('fetchAvailableModels') ||
    req.url.includes('loadCodeAssist') ||
    req.url.includes('fetchUserInfo') ||
    req.url.includes('listModelConfigs')
);

if (isAccountRpc) {
    const accounts = loadAllAccounts();
    const activeDefault = getActiveAccountEmail(accounts);
    boundEmail = (cascadeId && bindings[cascadeId]?.email) || activeDefault || 'Primary (Native)';
    if (isGen && cascadeId && !bindings[cascadeId] && boundEmail && boundEmail !== 'Primary (Native)') {
        setBinding(cascadeId, boundEmail);
        bindings[cascadeId] = { cascade_id: cascadeId, email: boundEmail, updated_at: new Date().toISOString() };
        logTraffic(`[AUTO_PIN] Chat: [${cascadeId}] permanently bound to: [${boundEmail}]`);
    }
    token = await resolveTokenForAccount(boundEmail);
    const tokenFp = token ? `token: ...${token.slice(-6)}` : 'token: [Native LS Session]';
    logTraffic(`${isGen ? 'ChatGen' : 'AccountRpc'}: [${cascadeId || 'general'}] -> Account: [${boundEmail}] | ${tokenFp} | Path: ${req.url}`);
} else {
    logTraffic(`ControlPlane: [${cascadeId || 'system'}] -> Native LS Session | Path: ${req.url}`);
}

const headers = { ...req.headers, host: UPSTREAM_HOST };
if (isAccountRpc && token) headers.authorization = `Bearer ${token}`;
```

### 2. Conversational Anchor & Extended Horizon
1. Added `setLastCascadeId(cascadeId, email)` to export the active conversation handle directly from `server.js`.
2. Extended conversation memory window from 30 seconds to 1 hour (`3600000 ms`), ensuring payload-less quota requests continue resolving the conversation's bound account even during prolonged reading or inactivity.

### 3. Immediate Active Account Synchronization (`api.js` & `multi_account_ui.js`)
1. In `api.js`, updated `/api/multi-account/bind` to unconditionally call `setActiveAccount(data.email)` and `setLastCascadeId(data.cascadeId, data.email)`.
2. Added dedicated endpoint `POST /api/multi-account/set-active` to allow instant propagation when switching between conversation tabs in the sidebar.
3. In `multi_account_ui.js`, updated `item.onclick` to pass `active: true` unconditionally, and added conversation switch detection in `render()` to immediately notify the router via `/api/multi-account/set-active`.

### 4. Binary & Packaging Redeployment
Executed `manage-antigravity.sh selector all --force` to repack `/opt/antigravity2/resources/app.asar` and patch `/opt/antigravity/resources/app/out/` with zero process termination.

---

## 4. Verification & Validation

1. **Syntax & Unit Tests**:
   - `node -c` validated all modified JS files (`server.js`, `api.js`, `multi_account_ui.js`, `multi_account_router.js`).
   - Node test suite `tests/test_router_quota_routing.js` verified `setLastCascadeId`, `POST /api/multi-account/set-active`, and `bindings.__active_account` synchronization.
   - Python test suite `tests/test_fixes_validation.py` executed: 72 tests passed cleanly.
   - Multi-account models and proxy tests: 9 tests passed cleanly.
2. **ASAR & Disk Inspection**:
   - Extracted patched `app.asar` and verified `isAccountRpc`, `setLastCascadeId`, and header rewriting logic present in `dist/router/server.js`.
   - Verified IDE `resources/app/out/router/server.js` synchronized.
