# Forensics Case 38: Custom Models "Invalid URL" Defect, Theme Adaptation, and Gateway Account Architecture

## Executive Summary
Following the deployment of the in-app Custom Models Settings UI patch (Case 37), attempting to use or activate custom models such as `cx/gpt-6.1-sol` yielded a generic `Invalid URL` error. Simultaneously, the injected UI was locked to dark palette hardcoded hex values (`#18181b`, `#202024`, etc.), breaking visual usability in Antigravity's Light Theme. Furthermore, users were forced to configure API endpoints and credentials per model rather than at the Gateway/Provider level.

This document records the exact root cause of the `Invalid URL` TypeError, the implementation of CSS-variable-based Dark/Light theme adaptation, and the realization of Gateway-level configuration where child models inherit endpoint URLs, tokens, and formats.

---

## 1. Root Cause Analysis: The `Invalid URL` Error

### 1.1 The Anomaly
When `cx/gpt-6.1-sol` was queried or validated, the client encountered:
```text
Invalid URL
```
or upstream error:
```text
Invalid model configuration: Invalid URL
```

### 1.2 Inspection of `custom_models.json` & `proxy.js`
In `~/.gemini/antigravity/custom_models.json`, models discovered or imported under provider `odirect` were stored with model identifiers, capabilities, and names, but without explicit per-model `apiUrl` or `apiKey` fields:
```json
{
  "id": "models/odirect-cx/gpt-6.1-sol",
  "model_id": "cx/gpt-6.1-sol",
  "provider": "odirect",
  "name": "cx/gpt-6.1-sol",
  "enabled": false
}
```

When Antigravity dispatched a request for `cx/gpt-6.1-sol`, `proxy.js` located the model, but in `customRequest.js`:
```javascript
const target = cloudCode || model.rawUrl ? model.apiUrl : registry.getProviderUrl(model.apiUrl, externalName, ...);
url = new URL(target);
```
Because `model.apiUrl` was `undefined`, JavaScript's native V8 runtime threw:
```javascript
TypeError: Invalid URL
```
The error message `Invalid URL` is the exact `e.message` produced by `new URL(undefined)`.

Furthermore, in `schemaValidator.js`:
```javascript
const validProviders = providers.map(p => p.id);
if (!validProviders.includes(provider)) { ... }
```
`odirect` was not included in `PROVIDERS`, causing any runtime validation checks on `provider: "odirect"` to fail validation and be skipped by `loadCustomModels()`.

---

## 2. Gateway-Level Inheritance & Provider Normalization

### 2.1 The Requirement
Users should configure an AI Gateway (Base URL, API Token, Protocol Format) once. All models residing under that Gateway must inherit these settings automatically without manual duplication.

### 2.2 Implementation in `modelStore.js`
`normalizeModelConfig` was enhanced with a two-pass resolution engine:
1. **Pass 1 (Defaults Discovery):** Identifies default base URLs and API credentials from the `gateways` dictionary, `providers` map, or sibling model configurations sharing the same provider ID.
2. **Pass 2 (Inheritance Application):** Any model entry lacking `apiUrl`, `apiKey`, or `apiFormat` automatically adopts the provider defaults discovered in Pass 1.
3. **`ModelStore.prepare` Safeguard:** When saving or mutating a single model under an existing Gateway, sibling provider attributes are automatically inherited if omitted.

### 2.3 Provider Extensibility
1. Added `odirect` to `providers.js`:
   ```javascript
   preset('odirect', 'ODirect (AI Gateway)', 'https://api.example.com/v1/chat/completions', 'openai', true)
   ```
2. Relaxed provider validation in `schemaValidator.js` to accept alphanumeric identifiers matching `/^[a-z0-9_-]+$/i`, enabling arbitrary custom gateways without core patch modifications.

---

## 3. Dark & Light Theme Adaptation

### 3.1 CSS Custom Properties Architecture
The hardcoded hex values in `customPreload.js` were replaced with adaptive CSS variables tied to Antigravity's / VS Code's native theme properties:
- `--agy-bg`: `var(--vscode-sideBar-background, ...)`
- `--agy-card-bg`: `var(--vscode-editor-background, ...)`
- `--agy-row-bg`: `var(--vscode-list-hoverBackground, ...)`
- `--agy-fg`: `var(--vscode-foreground, ...)`
- `--agy-border`: `var(--vscode-panel-border, ...)`
- `--agy-input-bg`: `var(--vscode-input-background, ...)`
- `--agy-input-fg`: `var(--vscode-input-foreground, ...)`
- `--agy-primary-bg`: `var(--vscode-button-background, ...)`

### 3.2 Selective Mode Overrides
Explicit styling overrides were added for:
- `body.vscode-light #agy-custom-models-section, body.vscode-light #agy-modal-overlay`
- `[data-theme="light"] #agy-custom-models-section, [data-theme="light"] #agy-modal-overlay`
- `.theme-light #agy-custom-models-section, .theme-light #agy-modal-overlay`
- `@media (prefers-color-scheme: light)`

This guarantees crisp contrast, clean borders, and optimal legibility regardless of whether the user operates in dark or light mode.

---

## 4. In-App Gateway Management Controls

In `customPreload.js`:
1. **Gateway Grouping:** Models are grouped by `provider` rather than duplicated per distinct model URL.
2. **`Configure Gateway` Button:** Opens a modal to inspect or update the Gateway Base URL, Token, and Format for all grouped models simultaneously.
3. **`+ Add Model` Button:** Pre-populates the Gateway's credentials so the user only provides the model identifier (e.g. `cx/gpt-6.1-sol`).
4. **`Discover Models` Button:** Queries the Gateway's `/models` endpoint using the Gateway token and imports selected models in batch.
5. **`+ Add Gateway` Button:** Enables registering a brand-new gateway endpoint from the main toolbar.

---

## 5. Verification & Test Evidence
1. **Model Loading Verification:** Verified in Node.js that `cx/gpt-6.1-sol` loads cleanly with valid `apiUrl`, `hasApiKey: true`, and `enabled: true`.
2. **Asar Archive Inspection:** Verified `customPreload.js`, `modelStore.js`, `proxy.js`, and `schemaValidator.js` inside `/opt/Antigravity-x64/resources/app.asar`.
3. **Pytest Regression:** All 214 test cases in the suite pass cleanly.
4. **Line Limits:** Verified all `.py` and `.sh` files remain strictly `<= 100 lines`.
