# Issue 69: Unified Experiments, Conversation Forking, Open-IDE, Native Context/Cost Telemetry & Multi-Account Usage Analytics

## Summary
Implemented a complete read-only usage/cost analytics suite and consolidated three overlapping UI/experiment patches (`Conversation Forking`, `Experiment Flags & Cost`, and `Open in IDE Button`) into a single atomic `experiments` patch (`[EX]`) targeting both Antigravity Desktop App (v2.36+) and Antigravity IDE.

---

## Key Components Implemented

### 1. Read-Only Token Usage & Cost Analytics (`src/antigravity_suite/usage/`)
- Added `pricing.py`, `scanner.py`, `render.py`, `cli.py`, and `bin/lib/sh/usage.sh` (`manage-antigravity.sh usage`, Control Center `[TU]`).
- Aggregates tokens (`input`, `cache_read`, `output`), Cache Hit Rate, USD spend, and cache savings per account (`bindings.json`) and per model across `transcript.jsonl` trajectories and CLI sessions, backed by `models.dev` cached pricing.

### 2. Unified Experiments, Forking & Open-IDE Consolidation
- **Single-Pass Patcher (`bin/lib/patch/patch_experiments.js`, `bin/antigravity-experiments-patch.js`):**
  - `patchAppExperiments` and `patchIdeExperiments` now coordinate DevUI server hooks, `experiments_catalog.js`, `patch_conversation_forking.js`, and `patch_open_ide.js` atomically, with symmetric `--unpatch` restoration.
  - Updated `patch_all.sh`, `patch_models_helpers.sh`, `suite_update*.sh`, `downgrade.sh`, CLI dispatchers (`cli_parse.sh`, `cli_dispatch.sh`), and Control Center (`[EX] Flags, Fork, Cost & IDE`) to manage the unified subsystem while retaining legacy CLI aliases (`fork`, `open-ide`).
  - Added `enable-open-in-ide-button` to `experiments_catalog.js` so the titlebar button reads `~/.config/antigravity/experiments.json` at runtime.

### 3. In-Process Ephemeral DevUI Server & Router Telemetry (`router/server.js`, `router/usage_live.js`, `router/api.js`)
- **App Ephemeral DevUI Server (`bin/lib/patch/experiments/dev_ui_server.js`):** Serves in-memory patched `main.js` from the embedded `language_server` ZIP bundle on `127.0.0.1:0` with a synchronous boot preamble setting `jetski.developer.customFlagOverrides`, `contextUsageIndicatorEnabled`, `globalThis.__SUITE_SIDEBAR_LIMIT`, and `globalThis.__SUITE_CONTEXT_TARGET`.
- **Router RPC Merging (`router/experiments.js`, `router/server.js`):** Routes `/v1alpha` and `:fetchLicenses` to `aicode.googleapis.com` and merges `experiments.json` into `:listExperiments` and `:fetchConfig` responses without dropping server payload fields.
- **Native `main.js` Surgical Patcher (`main_js_patcher.js`):**
  - Wraps `contextUsageIndicator:{Indicator:...}` safely (fixing `void 0` React crash).
  - Reprices `.costSummary` entries live using `models.dev` rates and replaces the circular dollar SVG with a non-circular bar chart icon.
  - Patches project/pinned sidebar conversation slicing (`patchSidebarChatLimit`) and `CheckpointConfigSchema` `maxTokenLimit` (`patchContextTarget`: `Default` / `256K` / `500K` / `1M`).
- **Stream Telemetry, Dashboard & Full-Text Search APIs (`router/usage_live.js`, `router/api.js`):**
  - Tracks live `TTFT`, `tok/s`, turn duration, per-turn cost/cache metrics, short-interval cache drop anomalies, and subagent usage stats (`/api/usage/active`).
  - Serves `/api/usage/dashboard` (per-account comparison, 53-week heatmap, model breakdown, recent sessions) and `/api/usage/search` (case-insensitive full-text transcript search).

### 4. Client UI Controls & Fixes (`suite_features_ui.js`, `experiments_ui_app.js`, `experiments_ui_ide.js`, `multi_account_ui.js`)
- Added detached PID-waiting relaunch (`relaunch_helper.js`) solving Linux `requestSingleInstanceLock()` exit-without-restart.
- Switched Artifact Pane Width CSS to override native `--max-artifact-width` (`56rem`, `80rem`, `none`).
- Replaced the `#suite-speed-telemetry-pill` text label with a compact gauge SVG icon anchored consistently in the right-hand `.agy-composer-footer` group across empty and active chats.
- Aligned the Account Selector chevron SVG in `multi_account_ui.js` to match Antigravity's native 14px `KeyboardArrowDownIcon` path.
- Added Compact Layout (`enable-compact-layout`), Full-Text Picker Search (`enable-fulltext-search`), `#L:C` File Context Menu (`enable-file-context-menu` + Electron `shell.showItemInFolder` / `shell.openPath`), Multi-Account Usage Dashboard modal (`Usage`), `Chats / Project`, and `Context Target` selectors.

---

## Verification
- `python3 -m unittest discover -s tests`: 263 tests passed (`OK`).
- `node --test tests/*.js`: 16/16 test suites passed (`fail 0`).
- `bash -n bin/manage-antigravity.sh bin/lib/sh/*.sh`: exited `0`.
- Verified `patchMainJs` and `node --check` on real App `language_server` `main.js` and IDE `jetskiAgent/main.js`, plus isolated stacked patch/idempotency/unpatch checks.
