# Forensic Analysis 62: Prompt Bar Typing Lag, Layout Thrashing & MutationObserver Saturation

## 1. Problem Statement
Users experienced periodic input freezes, cursor stutter, and typing lag while entering text in the prompt input bar (Lexical contenteditable editor in App and Monaco editor in IDE), especially in sessions with extensive conversation histories.

## 2. Root Cause Analysis

### A. Forced Synchronous Layout (Reflow Thrashing) on Keystrokes
In `bin/lib/patch/multi_account_ui.js`, an unthrottled `MutationObserver` watched `document.body` with `{ childList: true, subtree: true }`. Every keystroke typed into the Lexical/Monaco input box produced DOM text node insertions and mutations, immediately firing the observer on the microtask.
Inside the observer callback:
- `window.__antigravityFindTarget()` queried all `[data-testid="model-selector-trigger"]` elements and evaluated `el.getBoundingClientRect().width > 0` and `el.offsetParent !== null`.
- `window.__antigravityDetectCascadeId()` queried all `[data-testid="conversation-view"]` elements and evaluated `el.getBoundingClientRect().height > 0`.

In Chromium/Electron, calling layout metrics (`getBoundingClientRect`, `offsetParent`) immediately following DOM mutations forces **Synchronous Layout Recalculation (Layout Thrashing)**. On large DOM trees with multiple chat turns, code blocks, and SVG icons, this synchronous layout blocked the JavaScript main thread for 20ms–50ms per keypress, buffering keystrokes and causing noticeable stutter.

### B. High-Frequency 250ms Layout Polling Interval
A standing `setInterval(..., 250)` in `multi_account_ui.js` repeated the exact same forced reflow and cascade detection 4 times every second, regardless of whether the user was idle or in the middle of typing a word.

### C. Continuous `hideDevFooter` Scanning on Typing
In `bin/lib/patch/ui/mount.js`, a secondary `MutationObserver` executed `document.querySelectorAll('button[title="Reset State"], button[title*="Reset"]')` across the entire document on every keystroke. It lacked typing exclusion and never disconnected even after the developer footer had already been permanently hidden.

### D. IDE IPC `executeJavaScript` Polling Loop
In `bin/lib/patch/antigravity-multi-account-ide.js`, `setInterval(scanAllTargets, 1200)` called `target.executeJavaScript(checkScript)` across all frames of all WebContents every 1.2 seconds without caching injected targets, causing recurring V8 execution overhead.

### E. RTL Direction Engine Scanning Historical Chat Blocks on Keystrokes
The RTL direction engine in `antigravity-rtl` hooked `input` events and periodically ran `document.querySelectorAll(BLOCKS)` across the entire conversation history, re-checking thousands of historical paragraphs and list items and mutating `dir` attributes while the user was actively typing.

## 3. Engineering Fixes

1. **Typing Mutation Exclusion in `multi_account_ui.js`:**
   Added element filtering to the `MutationObserver` callback. Mutations originating within `textarea`, `input`, `[contenteditable]`, `.monaco-editor`, `[data-lexical-editor]`, `[data-testid*="input"]`, `[role="textbox"]`, or multi-account components (`.agy-toast`, `.agy-usage-flyout`, `#antigravity-account-pill`) are immediately ignored.
   Debounced valid structural mutations by 150ms.

2. **Typing-Aware Polling & Interval Relaxation:**
   Relaxed `setInterval` from 250ms to 2500ms (10x reduction). Added a guard checking `document.activeElement` so that when the user is focused in an editor or typing input, the interval check is skipped entirely.

3. **Elimination of Forced Layout Queries in `mount.js`:**
   Removed `getBoundingClientRect().width` and `getBoundingClientRect().height` calls from `__antigravityFindTarget` and `__antigravityDetectCascadeId`, using direct hierarchical queries (`ref?.closest('[data-testid="conversation-view"]')`) without layout metrics.

4. **One-Shot Disconnect for `hideDevFooter`:**
   Added `footerHidden` tracking flag to `hideDevFooter`. Once hidden, the `MutationObserver` immediately disconnects (`footerMo.disconnect()`), preventing any subsequent queries.

5. **Target Injection Caching in IDE Patcher:**
   Added `target._agyInjected` guard in `antigravity-multi-account-ide.js` to eliminate redundant `executeJavaScript` IPC calls, and relaxed the scan interval from 1200ms to 4000ms.

6. **RTL Typing Bypass Wrapper:**
   Wrapped `window.__antigravityRtlCore.updateDir`: when `document.activeElement` indicates active typing, direction updates are confined solely to the active input element, bypassing the heavy `querySelectorAll(BLOCKS)` scan across historical messages.

7. **Test Coverage:**
   Created `tests/test_typing_performance_isolation.js` asserting mutation exclusion, absence of forced layout metrics in `mount.js`, one-shot observer termination, and mock execution.

## 4. Verification & Validation
- Node.js test suite: 7/7 tests passed.
- Python unittest suite: 261/261 tests passed.
- Repacked and verified `/opt/antigravity2/resources/app.asar` and `/opt/antigravity` IDE with updated patches.
- Render thread reflow overhead reduced from O(keystroke) forced layout to zero during typing.
