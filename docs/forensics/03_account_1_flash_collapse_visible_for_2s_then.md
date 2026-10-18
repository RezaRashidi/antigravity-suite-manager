# Issue 2: Account 1 "Flash & Collapse" (Visible for 2s, Then Only Old Chats)

### Symptoms
* Launching Account 2 displayed all 306 chats continuously in a flat chronological list.
* Launching Account 1 displayed all 306 chats for the first 2 seconds; then the list disappeared, leaving only ~17 old chats from months ago.

### Diagnostic Methodology & Execution
1. **Comparing Instance Configurations**:
   Inspected differences between Account 1 (`~/.config/Antigravity/app_storage.json`) and Account 2 (`~/.antigravity-profile2/.config/Antigravity/app_storage.json`):
   ```python
   # Account 1:
   "projectsGroupBy": "project",
   "sidebar_section_display": "{\"onlyShowFirstFewConvos\":{\"all\":false,\"d21f8bda-a6ca-434d-a243-ee89f4924363\":false}}",
   "projectsOrder": ["d21f8bda-a6ca-434d-a243-ee89f4924363", ...]

   # Account 2:
   "projectsGroupBy": "none",
   "sidebar_collapsed_section_headers": []
   ```

2. **Querying Database for Project `d21f8bda...`**:
   Queried SQLite for conversations belonging to `project_id = 'd21f8bda-a6ca-434d-a243-ee89f4924363'`:
   * Exactly 17 conversations returned, with dates spanning June, July, August, and October 12 (the exact "old chats" seen by the user).

3. **Frontend Lifecycle Mechanics**:
   * **0 - 2 seconds**: React mounts with initial Redux state (`projectsGroupBy = "none"`). All 306 conversations render in a flat list.
   * **2 seconds**: Electron IPC returns stored preferences from `app_storage.json`.
   * **State update**: `projectsGroupBy` updates to `"project"`. React switches to the Project Accordion view.
   * Because `onlyShowFirstFewConvos` had all projects collapsed except `d21f8bda...` (CRM), the sidebar hid all recent chats and isolated only the 17 old CRM conversations.

### Solution Applied
* In `~/.config/Antigravity/app_storage.json`:
  ```json
  {
    "projectsGroupBy": "none",
    "projectsSortBy": null,
    "sidebar_collapsed_section_headers": [],
    "sidebar_section_display": "{\"onlyShowFirstFewConvos\":{\"all\":false}}"
  }
  ```
* Both accounts now share identical `"projectsGroupBy": "none"` configurations, rendering all 306 conversations continuously without layout collapse.

---
