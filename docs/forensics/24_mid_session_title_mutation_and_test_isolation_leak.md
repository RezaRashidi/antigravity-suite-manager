# Issue 22: Mid-Session Title Mutation & Test Suite Isolation Leak

## 1. Problem Description
During normal conversation workflows (e.g. conversation `7fd4f197`), users observed that switching models or writing markdown reports caused the conversation title to suddenly mutate mid-session to the header of an artifact (e.g. `# 📋 گزارش رخداد فنی: قطعی سرویس‌های Panel و Gholak در پروداکشن`), wiping out authentic conversation titles like `Gitlab CI Build Logs Analysis`.

---

## 2. Root Cause Analysis

### A. Indiscriminate Brain Artifact Globbing (`extractor_brain.py`)
`extract_brain_title()` used an unconstrained glob:
```python
for af_path in glob.glob(os.path.join(brain_folder, "*.md")):
```
Any markdown file created inside the conversation brain store (incident reports, postmortems, changelogs, scratch drafts) was parsed for `# ` headings. When an authentic title candidate was absent or bypassed, arbitrary artifact headers were elevated to conversation titles.

### B. Test Suite Isolation Leak (`discovery_roots.py`)
When running automated unit tests (`python3 -m unittest discover tests`), `test_ide_new_chat_title_transfers_to_app_properly` invoked `merge_histories()` with a temporary `user_home`. However, `get_candidate_homes()` unconditionally appended `os.path.expanduser("~")`:
```python
homes.add(os.path.expanduser("~"))  # Leaked host user directory into test runs
```
Because of this leak:
1. The test runner discovered the user's live profiles (`~/.config/Antigravity/User/globalStorage/state.vscdb`).
2. The test's empty master database had no `conversation_summaries.db` entries for live chats (`curr_title = ""`).
3. Fallback resolution elevated brain artifacts to titles.
4. The test wrote these artifact titles back to the host's real `state.vscdb`.
5. The host's background synchronizer (`antigravity-sync.service`) detected `state.vscdb` mutations and propagated the artifact title across all SQLite and annotation stores.

---

## 3. Implementation Fixes

1. **Restricted Brain Extraction ([extractor_brain.py](file:///home/reza/PhpstormProjects/antigravity-suite-manager/src/antigravity_suite/history/extractor_brain.py))**:
   Removed `glob.glob("*.md")`. Artifact title resolution is strictly restricted to designated planning files: `task.md`, `implementation_plan.md`, and `architecture.md`.

2. **Strict Test Isolation ([discovery_roots.py](file:///home/reza/PhpstormProjects/antigravity-suite-manager/src/antigravity_suite/history/discovery_roots.py), [discovery_pools.py](file:///home/reza/PhpstormProjects/antigravity-suite-manager/src/antigravity_suite/history/discovery_pools.py))**:
   When `user_home` is explicitly provided, `get_candidate_homes()` returns only that directory and never falls back to `~` or `REAL_HOME`. `scan_desktop_launchers()` is disabled in isolated mode.

3. **Scoped Logging ([resolver.py](file:///home/reza/PhpstormProjects/antigravity-suite-manager/src/antigravity_suite/history/resolver.py))**:
   Debug journals and audit logs are scoped directly to `effective_master`, preventing unit tests from appending diagnostic logs to host log files.

4. **Multi-Store State Restoration**:
   Restored authentic title `Gitlab CI Build Logs Analysis` across `conversation_summaries.db`, `annotations/7fd4f197*.pbtxt`, `conversations/7fd4f197*.db` (step 23 checkpoint), and `state.vscdb`.

---

## 4. Verification
- Regression test `test_get_candidate_homes_strict_isolation_when_user_home_provided` confirms isolated homes never leak host roots.
- Regression test `test_extract_brain_title_ignores_arbitrary_markdown_artifacts` confirms non-planning markdown files are rejected.
- All 148 unit tests pass in 3.6s with zero pollution to host databases or sync journal logs.
