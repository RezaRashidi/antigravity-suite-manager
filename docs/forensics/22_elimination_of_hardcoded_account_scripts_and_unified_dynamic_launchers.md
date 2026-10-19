# Issue 20: Elimination of Hardcoded Account Scripts & Dynamic Multi-Instance Architecture

## 1. Problem & Context

Earlier versions of the Antigravity Suite Manager maintained separate, bespoke shell scripts for individual accounts:
- `bin/lib/sh/account1.sh`
- `bin/lib/sh/account2.sh`
- `bin/lib/sh/account1_launcher.sh`
- `bin/lib/sh/account2_launcher.sh`
- `bin/lib/sh/account1_icon.sh`

### Architectural Deficits
1. **Logic Duplication**: Each script contained its own heredoc template for generating launcher shell scripts and `.desktop` entries. Changes to environment flags (`ELECTRON_OZONE_PLATFORM_HINT="x11"`), sandboxing logic (`chrome-sandbox`), or background daemon invocations had to be duplicated across three separate files (`account1.sh`, `account2.sh`, and `instance_create_app.sh`).
2. **Feature Drift**: When `--restart` / `-r` support and `/proc/<pid>/exe` stale RAM binary detection were introduced, only specific scripts received the fix, leaving custom instances or Account 1 vulnerable to stale in-memory executions after upgrades.
3. **Violated Multi-Instance Generalization**: The suite is designed to manage arbitrary $N$ instances (`create-instance app <id>`), but hardcoding Account 1 and Account 2 as separate physical files created artificial, brittle special cases.

---

## 2. Root Cause Analysis

The system suffered from the "Account Pair Fallacy" — the initial assumption that users only run two accounts (personal and work). As the suite scaled to support arbitrary multi-account profiles (`~/.antigravity-profile-app-<id>`), the legacy account scripts remained as technical debt.

Furthermore, updating the app on disk while an instance was running left stale processes in RAM (`/proc/<pid>/exe -> ... (deleted)`). Because Electron uses `requestSingleInstanceLock()`, launching an updated app simply focused the existing, stale in-memory window unless the launcher explicitly detected the deleted inode and terminated the stale process.

---

## 3. Implementation & Resolution

### A. Unified Dynamic Launcher Generator (`app_launcher.sh`)
Created [app_launcher.sh](file:///home/reza/PhpstormProjects/antigravity-suite-manager/bin/lib/sh/app_launcher.sh) containing:
* `write_dynamic_app_launcher()`: Parameterized generator taking target path, profile root, user data dir, WM class, desktop name, icon paths, password store flags, and symlink aliases.
  * Injects `--restart` and `-r` CLI switches.
  * Checks `/proc/<pid>/exe` for `(deleted)` references to automatically restart instances when binaries are updated on disk.
  * Binds `antigravity-apply-icon.py --focus` for instant window foregrounding.
* `write_app_desktop_entry()`: Parameterized `.desktop` generator eliminating duplicated desktop entries.

### B. Unified Instance Setup (`instance_app.sh`)
Created [instance_app.sh](file:///home/reza/PhpstormProjects/antigravity-suite-manager/bin/lib/sh/instance_app.sh) containing:
* `setup_app_instance(iid)`: Configures Instance 1 (Primary), Instance 2 (Account 2), or any Custom Instance ($N$) dynamically.
* `setup_app_profile_symlinks()`: Handles symlink trees for shared configs and conversations.
* Backward-compatible aliases `setup_account_1` and `setup_account_2` delegate directly to `setup_app_instance 1` and `setup_app_instance 2`.

### C. Primary Icon Synchronization (`icons_primary.sh`)
Created [icons_primary.sh](file:///home/reza/PhpstormProjects/antigravity-suite-manager/bin/lib/sh/icons_primary.sh) providing `ensure_primary_icons()`.

### D. Deletion of Bespoke Files
Permanently removed:
* `bin/lib/sh/account1.sh`
* `bin/lib/sh/account2.sh`
* `bin/lib/sh/account1_icon.sh`
* `bin/lib/sh/account1_launcher.sh`
* `bin/lib/sh/account2_launcher.sh`

---

## 4. Verification

1. **Unit Test Suite**: All 123 unit tests pass without regressions (`python3 -m unittest discover tests`).
2. **File Length Invariant**: Every code file in the repository satisfies the strict $\le 99$ lines constraint:
   - `app_launcher.sh`: 94 lines
   - `instance_app.sh`: 63 lines
   - `instance_create_app.sh`: 55 lines
   - `icons_primary.sh`: 36 lines
3. **CLI & Workflow Compatibility**:
   - `manage-antigravity.sh app1` -> Successfully delegates to `setup_app_instance 1`.
   - `manage-antigravity.sh app2` -> Successfully delegates to `setup_app_instance 2`.
   - `manage-antigravity.sh create-instance app 3` -> Successfully delegates to `create_app_instance 3`.
