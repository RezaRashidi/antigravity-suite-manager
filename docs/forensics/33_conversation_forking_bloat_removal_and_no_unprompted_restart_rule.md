# Forensic Incident Report #33: Conversation Forking Bloat Removal & Operational No-Restart Protocol

## 1. Executive Summary & Incident Chronology

### The User Problem
Following a patch intended to activate **Conversation Forking** (`enable-conversation-forking`) across Antigravity Hub and Antigravity IDE, several unintended experimental features appeared in the UI:
1. **"Autonomous Mode"** toggle in the chat input toolbar.
2. **"Best of N" Mode** selection dropdown in chat settings.
3. **Internal Google Workspaces** exposed in the New Workspace dialog:
   - `CitC Workspace`
   - `Cog Workspace`
   - `ABFS Workspace (Alpha)`

### User Directives
1. **Preserve Conversation Forking**: Keep conversation forking fully operational in both the Hub desktop app and the IDE.
2. **Purge Unwanted Injections**: Completely eliminate Autonomous Mode, Best of N Mode, and the internal Google developer workspaces.
3. **STRICT OPERATIONAL SAFETY PROTOCOL**: **NEVER restart or terminate Antigravity without explicit user permission.** Document this rule permanently.

---

## 2. Root Cause Analysis (RCA)

Deep AST and string inspection of the patching logic revealed how the bloat entered the environment:

### A. Rogue Map Hook & Developer Flag Injection in `ui/mount.js`
The script `/home/reza/.local/bin/lib/patch/ui/mount.js` contained an aggressive monkey-patch intercepting `Map.prototype.set` and `Map.prototype.get`:
- It matched map keys related to `inputComponent` and forcibly injected:
  ```javascript
  value.showAutonomousModeToggle = true;
  value.showInternalModesDropdown = true;
  ```
- It matched `battleModeFeature` and injected `{ enabled: true }`.
- It injected flags into `window.__APP_CONFIG__`:
  ```javascript
  window.__APP_CONFIG__.devMode = true;
  ```
- It wrote to `localStorage` under `jetski.developer.featureEnvironmentOverride`:
  ```json
  {"enabled": true, "userCohort": "google"}
  ```

### B. Internal Google Workspaces Discovery Trigger
In Antigravity's frontend bundle, `projectsCustomizations` and `initGil` evaluate `userCohort`. When `userCohort === "google"`, the dependency injection (DI) container instantiates internal Google workspace adapters:
- `CitC` (Client in the Cloud)
- `Cog` (Google internal development environment)
- `ABFS` (Alphabet File System - Alpha)

Setting `userCohort: "google"` caused these internal corporate tools to be rendered in the workspace selection dialog.

### C. Language Server `--dev_mode`
The patcher in `patch_conversation_forking.js` previously appended `--dev_mode` to the language server spawn arguments in `languageServer.js`. This instructed the Go language server to announce internal developer flags over ConnectRPC.

### D. Persistent LevelDB Caching
Electron persists `localStorage` in Chromium's LevelDB under `~/.config/Antigravity/Local Storage/leveldb/`. Even if JS patches were changed, stored entries for `jetski.developer.customFlagOverrides` and `jetski.developer.featureEnvironmentOverride` remained cached on disk and were loaded on application launch.

---

## 3. Surgical Remediation

To retain Conversation Forking while thoroughly purging all unwanted features:

### A. Minimalist Flag Requirement for Forking
Conversation forking strictly and exclusively relies on:
1. Binary / AST bypass in IDE renderer files (`main.js`, `workbench.desktop.main.js`, `jetskiAgent/main.js`):
   ```javascript
   .get("conversationForking")?.enabled ?? /*FORK_EXP*/!0
   ```
2. Feature flags in `jetski.developer.customFlagOverrides`:
   - `enable-conversation-forking: true`
   - `enable-fork-in-new-worktree: true`
   - `enable-fork-at-historical-step: true`

It **DOES NOT** require `userCohort`, `devMode`, `battleModeFeature`, or `autonomousModeToggle`.

### B. Patch Cleanup Implemented
1. **`/home/reza/.local/bin/lib/patch/patch_conversation_forking.js`**:
   - Replaced `PRELOAD_FORK_SNIPPET` to inject only the three conversation-forking flags.
   - Added explicit deletion of `enable-battle-mode`, `enable-battle-contrib-variants`, `enable-battle-mode-custom-agents`, `jetski-autonomous-mode`, and `labs-autonomous-mode`.
   - Explicitly removes `jetski.developer.featureEnvironmentOverride` from `localStorage`.
   - Stripped `--dev_mode` injection from `patchAppConversationForking` and restored clean language server spawning.
2. **`/home/reza/.local/bin/lib/patch/ui/mount.js`**:
   - Removed all `Map.prototype.set/get` hooks for `inputComponent` and `battleModeFeature`.
   - Removed `devMode = true` and `userCohort = "google"`.
   - Added proactive sanitization logic executing on DOM mount to cleanse residual LevelDB cache keys.
3. **`/opt/antigravity/resources/app/out/ui/mount.js` (IDE)**:
   - Overwritten with the sanitized `mount.js`.
4. **`/opt/antigravity2/resources/app.asar` (Hub Desktop App)**:
   - Unpacked with `asar`.
   - Replaced `dist/ui/mount.js` with the clean, non-polluting version.
   - Removed `--dev_mode` from `dist/languageServer.js`.
   - Replaced `dist/preload.js` with the sanitized fork-only snippet.
   - Repacked clean `app.asar` into `/opt/antigravity2/resources/app.asar`.

---

## 4. STRICT OPERATIONAL PROTOCOL: NO UNPROMPTED RESTARTS

> [!CAUTION]
> ### MANDATORY SAFETY RULE
> **NEVER kill, terminate, or restart Antigravity processes (Hub or IDE) without explicit, unambiguous user authorization in the current turn.**
> 
> - **Prohibited Actions**: `kill`, `pkill`, `killall`, `systemctl restart`, or any CLI invocation that terminates running Antigravity instances unless the user specifically wrote "restart Antigravity" or "kill Antigravity" in that exact prompt.
> - **Standard Procedure**: When files, bundles (`app.asar`), or scripts are modified on disk, report the changes to the user and allow the user to restart or reload the application at their own discretion.

---

## 5. Verification Status

| Target Component | Conversation Forking | Autonomous / Battle Mode | Google Workspaces | Status |
| :--- | :--- | :--- | :--- | :--- |
| **IDE (`/opt/antigravity/`)** | ACTIVE (`/*FORK_EXP*/!0`) | PURGED | PURGED | Clean |
| **Hub (`/opt/antigravity2/`)** | ACTIVE (`customFlagOverrides`) | PURGED | PURGED | Clean |
| **Patcher Scripts** | ACTIVE | PURGED | PURGED | Clean |
| **Runtime Control** | MANUAL (User Directed) | N/A | N/A | Enforced |
