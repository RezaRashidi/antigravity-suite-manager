# Case 37: In-App Custom Models Settings UI Injection & Multi-Patch Coexistence

## Summary
The user requested integrating Custom Models directly into Antigravity App's native Settings window (`Settings → Models & Usage`), matching the behavior of `ketabchi-ar/antigravity-add-model` rather than relying solely on external CLI commands or manual daemon flags. This case documents the vendoring of the runtime patch engine (`deploy.mjs`, `runtime-patch.mjs`, and `customPreload.js`), the automated coexistence resolution between the in-app patch and existing patches (`F5 Reload`, `RTL Typography`, `Multi-Account Selector`), and the CLI/menu dispatch integration.

## Root Cause & Technical Details

1. **Vendor AST In-App Injection (`deploy.mjs` & `runtime-patch.mjs`):**
   - The injection parses Antigravity App's `app.asar` using TypeScript AST analysis without evaluating unverified code.
   - It hooks `dist/main.js` via `require('./modelPatch/desktop').install()`.
   - It hooks `dist/languageServer.js` by starting the internal local proxy (`dist/modelPatch/proxy.js`) and injecting `__antigravityModelPatchUrl`.
   - It appends `customPreload.js` to `dist/preload.js`, which renders `#agy-custom-models-section` in DOM Settings, provides the "Add model" modal with auto-fetch and latency testing, and intercepts `parsed.models` API calls to display custom models in the model dropdown.

2. **Patch Coexistence Challenge:**
   - `deploy.mjs` strictly expects vendor JavaScript in `dist/languageServer.js` and `dist/preload.js` and refuses to patch an archive that already contains foreign hooks.
   - `antigravity-rtl` maintains its own backup file `app.asar.bak` and reverts to it when forced.
   - To achieve seamless multi-patch harmony, `patch_models_app()`:
     - Detects active flags for F5 reload, RTL typography, and multi-account selector.
     - Temporarily swaps to pristine base `app.asar.orig`.
     - Executes `deploy.mjs` to establish the core custom models runtime and backup.
     - Automatically cleans stale `app.asar.bak` and re-applies RTL, F5, and Selector on top of the patched base.
     - Idempotent and reversible via `manage-antigravity.sh unpatch-models`.

## Verification & Test Results
- Automated unit tests in `tests/test_patch_models.py` verified:
  - Script boundaries (`<= 100 lines` rule).
  - Clean `deploy.mjs --check` execution against standalone 2.24.0.
  - In-app DOM markers (`#agy-custom-models-section`, `injectCustomModelsSection`, `openModelModal`).
- Live verification on `/opt/Antigravity-x64/resources/app.asar` confirmed:
  - `ModelPatch present: True`
  - `In-App UI present: True`
  - `RTL present: True`
  - `Selector present: True`
- All 214 test cases in `pytest` pass cleanly.
