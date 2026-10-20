# Antigravity Multi-Account Selector Architecture & Engineering Specification

## 1. System Overview

The Multi-Account Selector subsystem enables seamless, per-conversation Google account routing, real-time quota telemetry, and native UI controls inside both the local Antigravity Desktop App (Electron) and Remote Control sessions (Web / Mobile).

```
+-----------------------------------------------------------------------------------+
|                            Antigravity Electron Host                              |
|                                                                                   |
|   +-----------------------+                    +------------------------------+   |
|   | Antigravity Renderer  |                    | Antigravity Main (Node.js)   |   |
|   |                       |                    |                              |   |
|   | [Account Pill Button] | <-- IPC / REST --- | [Multi-Account IPC Bridge]   |   |
|   | [Dropdown Selector]   |                    | [dist/ipcHandlers.js]        |   |
|   | [Usage Limits Flyout] |                    +---------------+--------------+   |
|   +-----------+-----------+                                    |                  |
|               | (DOM Injection via utils.js)                   |                  |
|               v                                                v                  |
|   +-----------------------+                    +------------------------------+   |
|   | React Chat Input UI   |                    | In-Process Loopback Router   |   |
|   | [Model Trigger Mount] |                    | http://127.0.0.1:41999       |   |
|   +-----------------------+                    +---------------+--------------+   |
+----------------------------------------------------------------|------------------+
                                                                 |
               +-------------------------------------------------+
               |
               v
+-----------------------------------------------------------------------------------+
|                        Multi-Account Proxy Router & Gateway                       |
|                                                                                   |
|  +--------------------+   +----------------------+   +-------------------------+  |
|  | Request Inspector  |   | Cascade Bindings Map |   | Account Vault & OAuth   |  |
|  | - StreamGenContent |   | - cascadeId -> email |   | - Primary (Native LS)   |  |
|  | - Slash Commands   |   | - global default     |   | - Secondary (Tokens)    |  |
|  +---------+----------+   +----------+-----------+   +------------+------------+  |
|            |                         |                            |               |
|            v                         v                            v               |
|  +-----------------------------------------------------------------------------+  |
|  | Header & Bearer Token Rewriter                                              |  |
|  | - Strips caller Authorization header                                        |  |
|  | - Injects target account Bearer token                                        |  |
|  +-----------------------------------+-----------------------------------------+  |
|                                      |                                            |
|                                      v                                            |
|                  +---------------------------------------+                        |
|                  | Upstream: daily-cloudcode-pa.goog...  |                        |
|                  +---------------------------------------+                        |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Subsystems

### 2.1 Reverse Proxy & Request Interceptor (`router/`)
- **Server (`router/server.js`)**: Listens on `0.0.0.0:41999` to service both local Electron renderer requests and remote devices accessing via Remote Control.
- **API Endpoints (`router/api.js`)**:
  - `GET /api/multi-account/state`: Synchronously returns active accounts, quotas, bindings, and active account defaults.
  - `POST /api/multi-account/bind`: Binds a specific conversation (`cascadeId`) to a chosen Google account.
  - `GET /ui_bundle.js`: Bundles styles, mount scripts, flyout templates, and UI controllers for zero-install bookmarklet injection on Remote Control browsers.
  - `tryInterceptCommand`: Intercepts in-chat slash commands (`/whoami`, `/accounts`, `/switch <id|email>`) directly inside the SSE event stream for mobile and browser users.

### 2.2 Account Vault & OAuth Management (`router/accounts.js`, `router/oauth.js`)
- Discovers accounts from GNOME Keyring / Secret Service (`jetski-standalone-oauth-token`) and fallback token storage (`~/.config/antigravity/accounts.json` or `jetski-standalone-oauth-token`).
- Refreshes expired Google tokens automatically via Google OAuth endpoints with exponential backoff and persistent token rotation.

### 2.3 Live Quota & Telemetry Engine (`router/telemetry.js`)
- Probes local LanguageServer ConnectRPC endpoint (`/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary`) for ultra-low latency (<50ms) primary account limits.
- Executes direct queries to `https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary` with Bearer tokens for secondary accounts.
- Dual-tier caching:
  - Non-blocking synchronous local cache (`loadAllAccountsWithQuotasSync`).
  - Asynchronous background cache hydration with a 3500ms network timeout and cache retention to prevent blank limits.

---

## 3. Frontend UI Injection (`bin/lib/patch/`)

### 3.1 Seamless Injection via `dist/utils.js`
- **Hook Placement**: Injected on both `win.webContents.on('dom-ready')` and `win.webContents.on('did-finish-load')`.
- **Dynamic Mounting (`ui/mount.js`)**:
  - Automatically locates the model selector button (`[data-testid="model-selector-trigger"]`).
  - Traverses the DOM hierarchy to mount `#antigravity-account-pill` immediately adjacent to the model trigger.
  - Fallbacks to `.@container/input-footer` and bottom toolbars during transitions.
  - Identifies active conversation via `window.location` regex and DOM data attributes (`data-cascade-id`).

### 3.2 UI Controller & Visual Components (`multi_account_ui.js`, `ui/flyout.js`)
- Pill button renders current account username (e.g., `rezalast4m`).
- Interactive dropdown lists all registered accounts with checkmark badges for the active chat.
- Flyout panel displays discrete SLA quota bars for:
  - **Gemini Models**: Weekly Limit Remaining and Five Hour Limit Remaining.
  - **Claude and GPT Models**: Weekly Limit Remaining and Five Hour Limit Remaining.
  - Live reset timestamps (e.g., resets in X days, Y hours).

---

## 4. F5 Backend Sync Architecture

### 4.1 Chat History Sync with IDE
- Antigravity Desktop App caches conversation summaries in the `language_server` memory space.
- Pressing `F5` or `Ctrl+R` triggers `onRestartRequested` in `dist/utils.js`:
  1. Checks if an agent is currently generating to prevent aborting running work.
  2. Restarts the local language server process (`ls.restartLanguageServer()`), which forces re-reading SQLite `conversation_summaries` from Antigravity IDE.
  3. Dynamically captures the new random listen port via `ls.getLsPort()`.
  4. Navigates `win.loadURL()` to the new port without dropping ConnectRPC state or causing HTTP connection errors.
  5. Automatically re-triggers `did-finish-load` to re-inject and mount the Account Selector.

---

## 5. Slash Command Auto-Suggestions

Antigravity auto-indexes skills defined in `~/.gemini/config/skills/` into the chat input autocomplete menu:
- `/whoami`: Displays active Google account, conversation bindings, and quota limits.
- `/accounts`: Lists all connected accounts, remaining percentages, and reset windows.
- `/switch <id|email>`: Immediately switches and binds the current conversation.

### Automated Skill Deployment
The skill manifests are tracked in the repository (`skills/whoami`, `skills/accounts`, `skills/switch`) and automatically deployed during:
- `make install`
- `~/manage-antigravity.sh selector`
- `~/manage-antigravity.sh install`

---

## 6. Verification and Coding Standards

- **Strict Line Limit Enforcement**: Every `.js` and `.py` file is strictly $\le 99$ lines to maximize maintainability and stay within context budgets.
- **Portability**: Zero hardcoded user directories or installation paths; dynamically resolves `/opt/antigravity2`, `/opt/antigravity`, or local user binaries.
- **Safety**: Safe error handling with try-catch guards around all DOM mutations and IPC calls.
