# Case 40: Gateway Credentials Inheritance, Manual Model Addition, and Free & Stealth Auto-Import

## 1. Executive Summary
In Antigravity Custom Models settings UI, users configuring gateways (e.g., ODirect `https://ai.odirect.app/v1`) encountered `Error: Enter a key for this new model` when:
1. Adding a new model manually within the "Discover Models" modal (`Enter model ID manually`).
2. Selecting discovered models and clicking `Add Selected Models`.
3. Clicking the auto-import button for free/stealth models.

Additionally:
- The auto-import button had an inconsistent, clunky Persian label (`وارد کردن خودکار مدل‌های free`) amidst English controls.
- Models containing `stealth` (e.g. `kc/stealth/glyph-cluster`) were not included in the automated import criteria alongside `free` models.

This forensic document details the root cause in `modelStore.js`, `modelManagement.js`, and `customPreload.js`, the implementation of automatic gateway credential inheritance, proper English control labeling, and filtering for both Free and Stealth models.

---

## 2. Root Cause Analysis

### 2.1 "Enter a key for this new model" Error
In `vendor/antigravity-model-proxy/dist/modelStore.js`:
```javascript
if (isMaskedSecret(model.apiKey) || model.apiKey === undefined) {
    if (isMaskedSecret(model.apiKey) && !existing?.apiKey)
        throw new Error('Enter a key for this new model');
    model.apiKey = existing?.apiKey || '';
...
```
1. In the renderer UI, `storageAPI.getCustomModels()` lists models with redacted API keys (`'********'`), which satisfies `isMaskedSecret(model.apiKey)`.
2. When creating any new model under a gateway (from discovery, manual entry, or auto-import), the new model's name does not match any existing model on disk (`existing` is `undefined`).
3. Furthermore, `copyFrom: gateway.name` was not supplied, and `modelStore.prepare()` did not inspect sibling models sharing the same `provider` or API origin for credentials when `existing` was absent.
4. Consequently, `isMaskedSecret(model.apiKey) && !existing?.apiKey` evaluated to `true`, throwing `Enter a key for this new model`.

### 2.2 Sibling Probe Lookup Deficit
In `modelManagement.js` `resolveProbe(input)`:
```javascript
const stored = input.name ? store.read().find((model) => model.name === input.name) : undefined;
```
If `input.name` was not an existing model, `resolveProbe` had no fallback to sibling models with the same provider, failing probes with redacted credentials.

### 2.3 UI Labeling and Filter Scope
- The button text was labeled in Persian `وارد کردن خودکار مدل‌های free`, clashing with the UI design (`Configure gateway`, `+ Add model`, `Discover models`).
- The regex `/free/i` failed to match `stealth` models such as `kc/stealth/glyph-cluster`.

---

## 3. Resolution & Architectural Design

### 3.1 Sibling Credential Inheritance in `modelStore.js`
In `ModelStore.prepare(input, existing)`:
- Look up sibling model configurations in the persistent store matching `item.provider === model.provider` or matching API URL origins.
- Set `keySource = (existing?.apiKey && existing.apiKey !== 'none') ? existing : sibling`.
- If `model.apiKey` is masked or empty, inherit `keySource.apiKey` and `keySource.encrypted` seamlessly.
- Inherit custom headers and default endpoint paths from sibling models as well.

### 3.2 Probe Fallback in `modelManagement.js`
In `resolveProbe(input)`:
- Fall back to stored models matching `input.provider` with valid API keys if `input.name` is not matched.

### 3.3 UI Refinement in `customPreload.js`
1. **Button Renaming**: Changed `وارد کردن خودکار مدل‌های free` to `Auto-import Free & Stealth`.
2. **Regex Expansion**: Updated filter to `/free|stealth/i.test(m.id || '') || /free|stealth/i.test(m.displayName || '') || /free|stealth/i.test(m.name || '')`.
3. **CopyFrom / Prior Preservation**: Passed `(prior ? { originalName: prior.name } : { copyFrom: gateway.name })` across all model creation paths in Discover modal and auto-import.
4. **Discover Toolbar Enhancement**: Added a one-click `Select Free & Stealth` button inside the Discover Models modal.

---

## 4. Verification & Testing
1. Tested `ModelStore.prepare()` with masked (`'********'`) and empty API keys on live `custom_models.json` with `provider: 'odirect'`. Correctly inherited encrypted machine key without throwing.
2. Verified error is still thrown if an entirely new provider without credentials or siblings is entered.
3. Re-deployed patch via `./manage-antigravity.sh patch-models --force`. Verified multi-patch coexistence (`RTL`, `F5`, `Selector`, `ModelPatch`).
4. Ran all 214 tests in `pytest`. All passed.
