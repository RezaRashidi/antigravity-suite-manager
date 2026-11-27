# Issue 68: Internal RTL Engine, Table Column Reversal, Bubble Alignment & OS Font Discovery

## Problem
The external `antigravity-rtl` (`v1.4.1`) dependency had five structural defects and tight coupling with Antigravity Suite patches:
1. **Intermittent auto-RTL drop during focus/streaming:** `bin/lib/patch/ui/mount.js` (`optimizeRtl`) wrapped `updateDir()` and returned early whenever `[contenteditable]` held focus, dropping live AI response updates while the prompt box remained focused. The observer also lacked `characterData: true` and judged paragraphs by the very first character including inline `<code>` and URLs.
2. **Broken Markdown tables under Force RTL:** `forceRTL` applied `direction: rtl !important` to `.leading-relaxed > *`, hitting `.md-table-host` and breaking Antigravity's bleed margins (`margin-inline-start`), `scrollLeft` overflow masks, and border dividers.
3. **FA Font weight mismatch on Linux Fontconfig:** Selecting family names such as `dana` matched `Dana Bold` (`weight: 700`) via `local('dana Bold')` while failing Regular weight (`400`) because Fontconfig/Blink `local()` resolves FullName/PostScriptName (`Dana Regular`, `Dana-Regular`).
4. **Prompt bubble & Multi-Account patch coupling:** Historical Persian `[data-testid="user-input-step"]` bubbles remained left-aligned when inner `.whitespace-pre-wrap` got `dir="rtl"` without tagging the card wrapper; `patch_multi_account_ui_inject.js` nested inside `/* ANTIGRAVITY RTL PATCH */` markers, risking removal on `unpatch-rtl`, and `antigravity-multi-account-ide.js` injected hardcoded RTL settings.
5. **External runtime dependency & overhead:** Relied on `npx antigravity-rtl@latest`, `patch_rtl_v234_shim.js`, GitHub network calls, forced `resize` events, and repeated full-history DOM queries.

## Architecture & Resolution
- **Self-contained module (`bin/lib/patch/rtl/`):**
  - `rtl_engine.js`: Code-stripped weighted RTL classifier (ignores `<code>`, `<pre>`, `.katex`, URLs, file paths, CLI flags, `.context-scope-mention`), `WeakMap` memoization per block/table/prompt-step, trailing-debounced `MutationObserver` (`characterData` + targeted block roots, unaffected by prompt focus), physical right-alignment tagging (`data-ag-rtl-bubble="1"`) for Persian user bubbles, and `table[dir="rtl"]` column reversal while keeping `.md-table-host` / `.md-table-scroll` LTR.
  - `rtl_styles.js`: Table border correction for reversed `table[dir="rtl"]`, multi-weight `@font-face` rules (`Regular`, `-Regular`, `Medium`, `SemiBold`, `Bold`), split static base-font `<style>` tag, zero `:has()` selectors, zero global Tailwind overrides, and `attachFontAutocomplete()` driven purely by OS font metadata.
  - `rtl_app_hook.js` & `rtl_ide_main.js`: Async `fc-list --format=%{family}\t%{lang}\t%{spacing}\n` catalog discovery (`{ all, fa, en, code }`) with zero hardcoded font names, serialized async writes to `~/.antigravity-rtl.json` via allowlist sanitization, and single-injection caching.
  - `rtl_ui_app.js` & `rtl_ui_ide.js`: Debounced settings UI with one-time `panelSeen` indicator dismissal and OS-sourced font dropdowns.
  - `patch_rtl.js` & shell/Python suite scripts (`patch_rtl.sh`, `patch_rtl_helpers.sh`, `unpatch_rtl.sh`, `status_inspect.py`, `suite_update_detect.sh`, `patch_models_helpers.sh`, `cli_dispatch_patches.sh`, `menu.sh`, `help.sh`, `control_center_patches.py`): Direct single-pass App/IDE patching/unpatching cleanly separated from `MULTI_ACCOUNT_UI_START`; retired `patch_rtl_v234_shim.js`.
- **Integration updates:**
  - `bin/lib/patch/ui/mount.js`: Bypasses legacy `optimizeRtl` wrapper when `_nativeTypingIsolation` is present.
  - `bin/lib/patch/patch_multi_account_ui_inject.js`: Anchors cleanly before `ANTIGRAVITY_SUITE_RTL_START` or `win.loadURL(url)`.
  - `bin/lib/patch/antigravity-multi-account-ide.js`: Reads `~/.antigravity-rtl.json` dynamically with schema sanitization.

## Verification
- `node --check` on all new/modified JS files (`bin/lib/patch/rtl/*.js`, `bin/lib/patch/antigravity-multi-account-ide.js`, `bin/lib/patch/patch_multi_account_ui_inject.js`, `bin/lib/patch/ui/mount.js`).
- `node tests/test_rtl_engine.js`: Verified code-stripped detection, streaming while focused, Persian/LTR table column reversal + `.md-table-host` LTR lock, historical bubble right-alignment, zero `:has()`, OS font catalog filtering, and legacy-to-internal migration preserving `MULTI_ACCOUNT_UI_START`.
- `node tests/test_typing_performance_isolation.js` and `python3 -m unittest tests/test_bash_features.py tests/test_ide_checksums.py tests/test_fixes_validation.py`.
- Applied via `manage-antigravity.sh rtl` to `/opt/Antigravity-x64` (`app.asar`) and `/opt/antigravity-ide` with valid `product.json` checksums.
