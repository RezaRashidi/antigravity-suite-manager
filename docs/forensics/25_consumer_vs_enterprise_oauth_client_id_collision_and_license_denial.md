# Forensic Case 25: Consumer vs. Enterprise OAuth Client ID Collision and "NO LICENSE" Denial

## 1. Incident Overview

When adding a secondary Google account via the Account Selector UI button (`+ Add Account`) or CLI (`manage-antigravity.sh multi-account login`), authentication in the browser succeeded, but the account in the selector flyout immediately failed telemetry and prompt routing:

```text
Usage limits
username@gmail.com
NO LICENSE
Subscription Required
This account does not have an active Gemini license.
```

Prompt generations routed to this account failed with HTTP 403 authorization errors, even though the account was valid and active.

---

## 2. Root Cause Analysis

### 2.1 Dual Client IDs in the Language Server Binary
The Google Antigravity binary (`language_server`) embeds two distinct Google OAuth Client IDs:

1. **Enterprise GCP / Cloud Code Client ID**:
   - `884354919052-***.apps.googleusercontent.com`
   - Secret Prefix: `GOCSPX-9YQW...`
   - Scope requirement: Google Cloud Platform organization administrator assignment.
2. **Consumer Antigravity Client ID**:
   - `1071006060591-***.apps.googleusercontent.com`
   - Secret Prefix: `GOCSPX-K58F...`
   - Scope requirement: Standard consumer Gmail & Google One AI entitlements.

### 2.2 First-Match Binary Regex Collision
In commit `b8e41ee`, dynamic binary extraction was introduced:
```python
m_sec = re.search(rb"GOCSPX-[a-zA-Z0-9_\-]{28}", raw)
m_cid = re.search(rb"\d+-[a-z0-9]+\.apps\.googleusercontent\.com", raw)
```
Inside `/opt/Antigravity-x64/resources/bin/language_server`:
- `884354919052` is located at byte offset `76212206`.
- `1071006060591` is located at byte offset `76220346`.

Because `re.search` picks the **first match**, the extraction returned the **Enterprise Client ID (`884354919052`)**.

### 2.3 Upstream Google Rejection
When tokens minted with `884354919052` were sent to `https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary`, Google checked for an Enterprise Cloud Code license in GCP:
```json
HTTP 403 Forbidden
{
  "error": {
    "code": 403,
    "message": "You do not have a valid license of this product. Please contact your administrator to request a license. If you are not an enterprise user and believe you are receiving this message as an error, please try using the latest version and logging in again."
  }
}
```
The router parsed HTTP 403 as `license_status: "no_license"`, and the UI rendered `NO LICENSE / Subscription Required`.

---

## 3. Systematic Resolution

1. **Targeted Consumer Client ID Matching**:
   Updated `src/antigravity_suite/multi_account/tokens.py` and `bin/lib/patch/router/oauth.js` to scan all matches in the binary and prioritize `1071006060591`, explicitly excluding `884354919052`.
2. **Official Consumer Scopes (`Ats`)**:
   Aligned `src/antigravity_suite/multi_account/oauth.py` with Antigravity core scopes:
   - `openid email profile`
   - `https://www.googleapis.com/auth/cloud-platform`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
   - `https://www.googleapis.com/auth/cclog`
   - `https://www.googleapis.com/auth/experimentsandconfigs`
3. **IDE Language Server Binary Recovery & Validation**:
   Hardened `patch_multi_account_ide.js` and `bin/lib/sh/patch_selector.sh` with functional ELF execution verification and automated recovery from Hub `language_server` if the IDE binary was corrupted.
