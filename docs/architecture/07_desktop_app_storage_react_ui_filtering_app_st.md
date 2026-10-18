# Desktop App Storage & React UI Filtering (`app_storage.json`)

Antigravity Hub Desktop App stores UI interaction state inside `~/.config/Antigravity/app_storage.json`:

```json
{
  "projectsOrder": "[\"a9b5a9cf-cfda-543d-9a7e-6cf8a15a7005\", \"f71fd387-c848-4215-bc99-44a007d79163\"]",
  "pinnedConversations": "[\"c99bd561-1ff5-4e7a-9774-60193bb967b5\"]",
  "archivedConversations": "[]",
  "conversationTitles": {
    "c99bd561-1ff5-4e7a-9774-60193bb967b5": "Performance Engineering Strategy: Load Test Catalog"
  }
}
```

> [!IMPORTANT]
> The Desktop App writes `projectsOrder`, `pinnedConversations`, and `archivedConversations` as **JSON-stringified strings** (`"[\"uuid\"]"`), not native arrays. Parsers must support string-encoded JSON decoding.

---

### 7.1 The React Double-Elimination Filter (`w.has(ta)`)

Extracted from `/opt/antigravity2/resources/app.asar` (Webview bundle `/tmp/hub_ui_main.js`, lines 8030–8040):

```javascript
// Source: resources/app.asar (decompiled main.js - Component Asb)
var Asb = a => {
  var b = a?.headless ?? !1,
      c = cS(),                                      // Active sidebar project sections
      e = bk(),
      f = Lj();
  var g = f.get("projectManagementFeature");
  var t = Pj(a?.projectsStateProvider),             // Project state provider
      u = (0, A.useMemo)(() => t ?? [], [t]),
      v = fsb(),
      
      // w: Set of all registered project IDs across sidebar sections and projectsStateProvider
      w = (0, A.useMemo)(() => {
        var na = new Set(c.map(uh));
        u.forEach(Aa => { na.add(Aa.project.id); });
        return na;
      }, [c, u]),
      
      x = (0, A.useMemo)(() => new Set(u.map(na => na.project.id)), [u]),
      
      // y: The conversation filter callback
      y = (0, A.useCallback)(na => {
        var Aa = w.size === 0;
        return na.filter(Ca => {
          var ta = Ca.summary.trajectoryMetadata?.projectId;
          // CRITICAL BUG LOCATION:
          // If conversation has a projectId (ta) != "outside-of-project",
          // it MUST be in `w` (projectsOrder). Otherwise, it is silently dropped!
          return Ca.summary.cloud 
            ? !!ta && x.has(ta) 
            : Aa || !ta || ta === "outside-of-project" ? !0 : w.has(ta);
        });
      }, [w, x]),
      
      B = (0, A.useMemo)(() => y(r), [y, r]),
      C = (0, A.useMemo)(() => (m ? y(q) : B).filter(na => {
        na = na.summary.trajectoryMetadata?.projectId;
        return !na || !v.has(na);
      }), [m, y, q, B, v]);
      
  // Reads projectsOrder directly from ~/.config/Antigravity/app_storage.json
  var [N, O] = zN("projectsOrder", cZ, Frb, []);
  ...
};
```

#### Diagnostic Breakdown:
- When a user opens projects in IDE or another profile, new `projectId` UUIDs (e.g. `k6` `a9b5a9cf...`) get stamped into `<uuid>.db`.
- When Desktop App Profile 2 loads, `projectsOrder` in `~/.antigravity-profile2/.config/Antigravity/app_storage.json` only contained 14 projects.
- `w.has(ta)` returned `false` for `k6` and other non-listed projects, immediately discarding 162 conversations from the UI.

---

### 7.2 Pinned and Archived Membership Predicates

Extracted from `main.js` (lines 8035–8045):

```javascript
// Source: resources/app.asar (decompiled main.js - Conversation Set Evaluators)
{
  kind: "set",
  name: "pinned",
  // A conversation is ONLY pinned if Protobuf Tag 15 -> Tag 12 (pinned) is true AND not archived
  isMember: a => !!a.annotations?.pinned && !a.annotations?.archived
},
{
  kind: "set",
  name: "sidebar",
  isMember: a => !a.annotations?.archived && !a.annotations?.pinned
},
{
  kind: "set",
  name: "archived",
  isMember: a => !!a.annotations?.archived
}
```

```javascript
// Source: resources/app.asar (decompiled main.js - Storage Binding)
function dZ() {
  // Reads pinned order from app_storage.json
  return zN("pinned_conversations_order", cZ, Crb, []);
}
```

---
