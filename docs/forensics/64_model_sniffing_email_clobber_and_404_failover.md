# Issue 62: Model Sniffing Account Clobbering to Primary Native and HTTP 404 Model Failover

## 1. Problem Statement
When running multi-turn interactions or sub-steps on specialized models (e.g., `gemini-4-hydrogen-medium`), the session succeeded on the first step, but subsequently crashed with:
```
Agent execution terminated due to error.
Error: HTTP 404 Not Found
{
  "error": {
    "code": 404,
    "message": "Requested entity was not found.",
    "status": "NOT_FOUND"
  }
}
```

## 2. Root Cause Analysis
1. **Premature Variable Use in RPC Model Sniffing:**
   - In `bin/lib/patch/router/server.js`, model sniffing for `streamGenerateContent` was executed at the top of `if (isAccountRpc)`.
   - At that line, `boundEmail` had not yet been computed from `bindings` or `activeDefault`; it was initialized to its declaration default `'Primary (Native)'`.
   - Calling `setBinding(cascadeId, boundEmail, modelMatch[1])` wrote `"email": "Primary (Native)"` into `bindings.json` for that active chat.
2. **Account Clobbering in Multi-Turn Requests:**
   - On the immediate next tool call or subsequent prompt in the same trajectory, `server.js` resolved `bindings[cascadeId].email` which was now `'Primary (Native)'`.
   - The native session credentials lacked entitlements for restricted experimental models (such as Hydrogen), leading upstream Google API to return `HTTP 404: Requested entity was not found`.
3. **Missing HTTP 404 Failover:**
   - The router previously only intercepted `HTTP 403` and `HTTP 401`. `HTTP 404` errors were piped directly to the client without failover to an account possessing valid entitlements.

## 3. Resolution
1. **Reordered Computation:**
   - Moved model sniffing and `setBinding` in `server.js` until after `boundEmail` is resolved.
   - Guarded target email: only pass `boundEmail` if it is a real account, otherwise pass `null`.
2. **Guarded `setBinding` & `setActiveAccount`:**
   - In `bin/lib/patch/router/bindings.js`, `setBinding` now ignores `'Primary (Native)'` as an incoming email if a valid account was already bound, preserving the existing user account.
   - `setActiveAccount` ignores `'Primary (Native)'`.
3. **HTTP 404 Generation Failover:**
   - In `server.js`, extended candidate error handling to include `HTTP 404` on generation requests (`upRes.statusCode === 404 && isGen`).
   - If an account reports `model_not_found` / `Requested entity was not found`, the router records a transient cooldown and fails over to the next healthy account.
4. **Data Sanitization:**
   - Existing chat bindings that had been corrupted to `'Primary (Native)'` were sanitized back to standard fallbacks.
