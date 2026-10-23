# Forensic Case 30: Full Codebase Dynamic Instance and Account Orchestration

## 1. Executive Summary

### 1.1 Incident Overview
Following the elimination of phantom directories and keyring unlock prompt issues, an exhaustive codebase audit was conducted to fulfill the user requirement: **"چک کن همه جا دینامیک باشن"** (Ensure all areas are 100% dynamic).
Previously, certain menus, tables, and scripts had hardcoded references to "Account 1", "Account 2", or "IDE (Primary)" regardless of whether secondary accounts or clone profiles actually existed. Furthermore, multiple installation and update bash scripts used `||` (OR) rather than `&&` (AND) when testing for Account 2, which inadvertently regenerated desktop entries or launched account-2 configuration routines when an orphaned directory existed.

### 1.2 Root Cause Analysis
1. **Static Table Formatting**:
   - `bin/lib/sh/status_checker.py` statically printed `Antigravity (Acc 1&2)`, `• Antigravity (Acc 2): ...`, and `• Account 2 Status: ...` regardless of actual installation.
   - `bin/lib/sh/instance_list.py` hardcoded `Antigravity (Acc 1)` and `Antigravity IDE (1)` even when only one account/IDE was configured.
2. **Defective Conditional Logic (`||` vs `&&`)**:
   - In `install_apps.sh`, `suite_update.sh`, `suite_update_components.sh`, `paths_wizard.sh`, and `step_8.sh`, the check was:
     `if [ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]; then`
     If an empty folder existed or a stale file remained, the scripts treated Account 2 as active.
3. **Hardcoded Labels in Interactive Menus & Handlers**:
   - `menu.sh` and `icons_menu.sh` displayed "Install / Update Antigravity App (Both Accounts)" even for single-account systems.
   - `src/antigravity_suite/cli/keyring.py` printed `[OK] Switched Account 2 to NORMAL mode` when switching `all` targets, even when Account 2 was nonexistent.

---

## 2. Dynamic Remediation

### 2.1 Dynamic Account & Instance Identity
- When a single account exists:
  - App is labeled cleanly as **`Antigravity`** or **`Antigravity App`**.
  - IDE is labeled cleanly as **`Antigravity IDE`**.
  - Default launcher path is `~/.local/bin/antigravity` (or `~/.local/bin/antigravity-ide`).
  - WM_CLASS defaults to `antigravity` and `antigravity-ide`.
- When multiple accounts or clone profiles genuinely exist:
  - App dynamically switches to **`Antigravity (Acc 1)`** or **`Antigravity (Account 1 - Default)`**.
  - Secondary clone is labeled **`Antigravity (Account 2)`** or **`Antigravity (App: <name>)`**.
  - Primary IDE switches to **`Antigravity IDE (Primary)`** only when additional IDE clone profiles exist.

### 2.2 Strict Existence Guards
- Replaced all occurrences of `[ -d "$PROFILE2_DIR" ] || [ -f "${LOCAL_BIN}/antigravity-acc2" ]` with:
  `[ -d "$PROFILE2_DIR" ] && [ -f "${LOCAL_BIN}/antigravity-acc2" ]`
- Updated Python detection logic across `clones_scan_app.py`, `clone_keyring_icon.py`, and `x11_apply.py` to enforce that Account 2 requires both the profile directory and an actual launcher.

### 2.3 Status & Keyring Menu Decoupling
- `status_checker.py`: Suppressed Account 2 theme badges, status rows, and labels when `has_acc2` is false.
- `keyring.sh` and `keyring.py`: When Account 2 is absent, the keyring options and command handlers dynamically toggle only between Antigravity App, Antigravity IDE, and all existing instances.

---

## 3. Verification & Architecture Compliance

1. **Line Count Verification**:
   - `find src bin scripts -type f \( -name "*.py" -o -name "*.sh" \) -exec wc -l {} + | awk '$1 > 100 && $2 != "total"'` returned **0 files**.
   - Every modified file strictly honors the rule: **<= 100 lines per file**.
2. **Automated Unit Testing**:
   - All 173 unit tests in `pytest tests/` pass completely.
   - Added `test_ide_clones_dynamic_naming` to verify single-instance vs multi-instance dynamic labeling.
3. **Interactive Menu Validation**:
   - `manage-antigravity.sh` Control Center displays 2 instances: `Antigravity IDE` and `Antigravity`.
   - `manage-antigravity.sh --classic-menu` displays option 3 as `Install / Update Antigravity App` and option 7 as `Create Secondary Account`.
   - `manage-antigravity.sh status` displays `Antigravity App` and omits Account 2.
