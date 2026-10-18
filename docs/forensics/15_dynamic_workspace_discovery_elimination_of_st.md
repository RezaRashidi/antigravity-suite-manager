# Issue 14: Dynamic Workspace Discovery & Elimination of Static Container Assumptions

### Symptoms
* On machines without standard JetBrains folder paths (e.g., custom structures like `/data/repos/`, `/home/user/work/`, `/srv/projects/`), chats created without selecting a project (`outside-of-project`) failed to normalize to their authentic workspace root.
* Subfolder tool calls (`Cwd`, `AbsolutePath`) either failed validation or fell back to raw deep paths rather than grouping under the actual project opened in the IDE.
* Hardcoding `PROJECT_CONTAINERS` (`phpstormprojects`, `webstormprojects`, etc.) caused machine-specific disparities between primary and secondary environments.

### Root Cause
1. **Static Container Heuristic**: `PROJECT_CONTAINERS` was a fixed Python set. If a developer's parent directory was not named in this set, subfolder truncation failed.
2. **Incomplete Workspace Discovery**: `discover_workspace_roots()` inspected `workspaceStorage/*/workspace.json` but ignored VS Code's primary global storage database (`state.vscdb`), specifically `history.recentlyOpenedPathsList`. Workspaces opened via IDE on non-standard paths were not registered into `KNOWN_ROOTS`.
3. **Marker File Traps**: Attempting to deduce project roots from generic project markers (`package.json`, `composer.json`, `Makefile`) is flawed in monorepo, microservice, and nested package setups (e.g., `/monorepo/frontend/package.json` would be falsely treated as a distinct root instead of the parent `/monorepo` opened in the IDE). In Antigravity, a workspace is *strictly and exclusively* a folder the user actually opened in the IDE or Hub.

### Solution Applied
1. **IDE Global Storage Ingestion**: Implemented [projects_vscdb_roots.py](src/antigravity_suite/history/projects_vscdb_roots.py) to query `state.vscdb` (`history.recentlyOpenedPathsList`) across all user profiles, retrieving all authentic folders opened by the user regardless of filesystem location.
2. **Dynamic Container Learning**: Updated [projects_roots.py](src/antigravity_suite/history/projects_roots.py) so that when authentic workspace roots are discovered (from `config/projects/*.json` or `state.vscdb`), their immediate parent folder names are automatically registered into `PROJECT_CONTAINERS`.
3. **Configurable Extensibility**: Added `load_dynamic_containers()` in [projects_constants.py](src/antigravity_suite/history/projects_constants.py) to load custom container directory names from `~/.config/antigravity/paths.conf` (`PROJECT_CONTAINERS="..."`) or environment variable `ANTIGRAVITY_PROJECT_CONTAINERS`.
4. **Prefix Matching Priority**: [projects_normalize.py](src/antigravity_suite/history/projects_normalize.py) matches against authentic known opened roots using longest prefix matching. If a path does not belong to any opened workspace, it stays `outside-of-project` rather than guessing or corrupting filesystem roots.
5. **Regression Verification**: Added `test_dynamic_container_learning_and_vscdb_discovery` in [tests/test_projects.py](tests/test_projects.py). All 114 tests passing.

---
