# Issue 61: Per-Chat Account & Model Persistence with Dynamic Fallback

## 1. Problem Statement
In multi-account workflows, chats may be bound to different Google accounts (e.g., `user1@example.com` with Pro/Hydrogen entitlements vs. a secondary account `user2@example.com` with standard quotas). Previously:
1. The binding mechanism only tracked `email` per chat ID (`cascadeId`).
2. When switching between conversations, the active account switched, but the model selection in Antigravity's model dropdown remained fixed on whatever model was last active in the previous chat (e.g., `Gemini 4 Hydrogen`).
3. If the newly active account lacked access to that model (or if the model was unsupported by that account's tier), prompt generation failed or errored out.
4. Model changes made within a chat were not persisted across chat switches.

## 2. Root Cause Analysis
- `bindings.json` schema stored `{ cascade_id, email, model, updated_at }`, but `model` was populated with an empty string `""` on every bind.
- Router endpoints `/api/multi-account/bind` and `/api/multi-account/set-active` did not process or save `data.model`.
- `multi_account_ui.js` only dispatched `antigravity:account-switched` on chat switch without inspecting or restoring the chat's selected model.
- There was no automated UI synchronization between the active account's available model configs (`cascadeModelConfigData.clientModelConfigs`) and the chat's restored model, causing invalid model persistence across accounts.

## 3. Resolution & Architectural Design

### A. Router & Bindings Layer
1. **Preservation of Existing State:** In `bin/lib/patch/router/bindings.js`, `setBinding(cascadeId, email, model)` preserves existing model and email values if not explicitly overwritten.
2. **RPC Model Sniffing:** In `bin/lib/patch/router/server.js`, generation RPC requests (`streamGenerateContent`) automatically extract the active model via regex `/"(?:model|modelName|model_name)":\s*"([^"]+)"/` and persist it to `setBinding`.
3. **API Endpoints:** `/api/multi-account/bind` and `/api/multi-account/set-active` in `bin/lib/patch/router/api.js` accept and persist `model`.

### B. UI Mount & Selector Synchronization (`mount.js`)
1. **Model Reader:** Exported `window.__antigravityGetSelectedModel()` which extracts the active model label from `[data-testid="model-selector-trigger"]`.
2. **Model Selector & Fallback:** Exported `window.__antigravitySelectModel(targetModelName, availableConfigs)`. It validates the target model against `availableConfigs`. If the account does not support the target model (e.g. Hydrogen on an account lacking it), it dynamically falls back to an available model (Flash/Pro) and triggers Radix selection.

### C. Multi-Account UI Controller (`multi_account_ui.js`)
1. **Chat Switching Restoration:** When switching chats (`cascadeId !== newCid`), calls `handleChatModelRestoration(newCid)` to restore the chat's saved model or fallback if unavailable on the newly active account.
2. **In-Chat Change Detection:** Listens to model selector changes in `document.addEventListener('click')` and `checkPillAndCascade()`, automatically syncing new model selections to `/api/multi-account/bind`.
3. **Manual Account Switch Fallback:** When manually switching an account via the pill dropdown, schedules model validation and fallback to ensure the current model is valid on the new account.
4. **Draft Promotion:** Transfers both account email and saved model when promoting draft chat IDs to persistent UUIDs.

## 4. Verification & Testing
- `tests/test_chat_switch_model_refresh.js` expanded with:
  1. Multi-chat account switch verification.
  2. Model restoration across chats (Hydrogen on Chat 1, Flash on Chat 2).
  3. Dynamic fallback to Flash when an account lacks Hydrogen.
  4. In-chat model change detection and persistence to `/api/multi-account/bind`.
- All 264 Python unit tests and all JS test suites passed cleanly.
