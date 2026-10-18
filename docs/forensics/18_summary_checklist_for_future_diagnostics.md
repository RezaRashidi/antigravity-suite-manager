# Summary Checklist for Future Diagnostics

| Checkpoint | Target Path / Command | Expected Healthy State |
| :--- | :--- | :--- |
| **Protobuf Tag 20** | `src/antigravity_suite/proto/cascade.py` | Must NOT emit Tag 20 when `source == 0` |
| **Protobuf Tag 1 vs 2** | `src/antigravity_suite/proto/cascade.py` | Tag 1 = Clean Title, Tag 2 = Preview Prompt |
| **Checkpoint Step 23** | `src/antigravity_suite/history/extractor.py` | Decodes `Tag 30 -> Tag 4` from `<uuid>.db` for authentic LLM title |
| **Timestamp Floor** | `src/antigravity_suite/history/item_metadata.py` | Normalized ms > Jan 1, 2020; prevents "2027y" epoch 0 bug |
| **Deletion Sync** | `src/antigravity_suite/history/deletion.py` | Bidirectional purge when `<uuid>.db` is removed; prevents infinite spinner |
| **Tray Icon Paths** | `~/.local/share/icons/` | `antigravity-1-tray.png` & `antigravity-acc2-tray.png` (48x48, 32x32, 24x24) |
| **Launcher Tray Env** | `~/.local/bin/antigravity-1`, `antigravity-acc2` | Exports `ANTIGRAVITY_TRAY_ICON_PATH` |
| **Tray Cache Sync** | `src/antigravity_suite/icon/tray_sync.py` | Scans `tempfile.gettempdir()`, `$TMPDIR`, `$XDG_RUNTIME_DIR`, `/run/user/<uid>`, `/tmp` |
| **Dynamic Workspaces** | `src/antigravity_suite/history/projects_roots.py` | Queries `state.vscdb` (`recentlyOpenedPathsList`); dynamically learns containers |
| **Hub vs IDE Partition** | `conversation_summaries.db` | `app_data_dir`: `antigravity` (Hub) vs `antigravity-ide` (IDE) |
| **Hub Binary Proto** | `agyhub_summaries_proto.pb` | Contains ONLY Hub partition chats (~53), NOT IDE workspace chats |
| **IDE State** | `state.vscdb` (`trajectorySummaries`) | Contains ALL workspace chats (293) |
| **Audit Log** | `~/.gemini/antigravity/history_merger_audit.log` | JSONL records for all mutations |
| **Language Server Health** | `~/.config/Antigravity/logs/language_server.log` | `reconcile checked N, restored 0, cached N, dropped 0` |
| **F5 Backend Reload** | `src/../bin/lib/patch/patch_utils_reload.js` | Invokes `await ls.restartLanguageServer()` & strips stale handlers |
| **Unit Test Suite** | `python3 -m unittest discover tests` | All 120 tests passing |
