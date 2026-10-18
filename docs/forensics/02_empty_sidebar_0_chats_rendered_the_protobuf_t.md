# Issue 1: Empty Sidebar (0 Chats Rendered) — The Protobuf Tag 20 Gate

### Symptoms
* SQLite (`conversation_summaries.db`) contained 306 conversations with valid titles, step counts, and workspace URIs.
* Go Language Server log (`~/.config/Antigravity/logs/language_server.log`) reported:
  ```
  [Summaries] reconcile checked 322 conversations, restored 0, cached 321, skipped 1, dropped 0, cancelled false in 71ms (resident: 0 -> 0)
  ```
* Yet, the Desktop App and IDE sidebar displayed **0 conversations** (completely blank project list).

### Diagnostic Methodology & Execution
1. **Backend vs. Frontend Isolation**:
   Because `reconcile_summaries.go` confirmed `cached 321, dropped 0`, the backend Go language server had successfully parsed and held all summaries in memory. The elimination was occurring in the frontend Webview bundle.

2. **Extracting Live Webview Frontend**:
   The Antigravity UI is rendered via an internal Webview loaded from the Language Server's local HTTPS port.
   * Extracted CSRF token and HTTPS port from process arguments:
     ```bash
     ps aux | grep language_server
     # Found: --extension_server_port 41693 --csrf_token dafc01cf-728b-473c-b172-6ef68a5a6f77
     ```
   * Downloaded `main.js` (the minified React frontend bundle) using loopback HTTPS with `x-codeium-csrf-token`.

3. **Tracing the Redux Ingestion Reducer**:
   Searched for trajectory batch updates in `main.js`:
   ```javascript
   const una = Ul({
     name: "trajectorySummaries",
     initialState: lna,
     reducers: {
       applyStreamBatch(a, b) {
         a.hasLoadedInitialSummaries = !0;
         for (let [e, f] of b.payload.updates) {
           let g = e, h = f;
           ...
           mna(h.source) ? (
             // Normal sidebar branch
             a.summaries[g] = ...;
             a.indexes.sidebar.add(g);
           ) : (
             // External conversation branch
             a.externalSummaries[g] = ...;
           )
         }
       }
     }
   });
   ```

4. **Inspecting the `mna(source)` Gate**:
   Extracted the implementation of `mna`:
   ```javascript
   function mna(a) {
     return a === T.CortexTrajectorySource.UNSPECIFIED || // 0
            a === T.CortexTrajectorySource.JETBOX ||      // 18
            a === T.CortexTrajectorySource.CIDER;         // 20
   }
   ```
   * Enum values: `UNSPECIFIED = 0`, `CASCADE_CLIENT = 1`, `JETBOX = 18`, `CIDER = 20`.
   * For local conversations, Google Antigravity omits Tag 20 on the wire (`source == 0`), so `mna(0)` evaluates to `true`.

5. **Root Cause Identification**:
   * Git history revealed commit [`6e08074`](https://github.com/RezaRashidi/antigravity-suite-manager/commit/6e08074) added:
     ```python
     # Tag 20: source (1)
     out += encode_tag_uint(20, 1)
     ```
   * Because Tag 20 was hardcoded to `1` (`CASCADE_CLIENT`), `mna(1)` returned `false`.
   * **Result**: Every incoming conversation summary was diverted to `externalSummaries`, completely bypassing `indexes.sidebar`.

### Solution Applied
* In [src/antigravity_suite/proto/cascade.py](src/antigravity_suite/proto/cascade.py), omit Tag 20 when `source == 0`:
  ```python
  if source != 0:
      out += encode_tag_uint(20, source)
  ```
* In [src/antigravity_suite/history/merger.py](src/antigravity_suite/history/merger.py), detect existing stored summaries with `source == 1` or `tag 20 == 1` and force a clean rebuild.
* In [src/antigravity_suite/history/sqlite_store.py](src/antigravity_suite/history/sqlite_store.py), strip `'CORTEX_TRAJECTORY_SOURCE_CASCADE_CLIENT'` from SQLite store.

---
