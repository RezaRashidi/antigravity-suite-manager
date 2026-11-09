# Forensic Analysis Case 54: Resolution of Smart Update Failure Caused by Missing `ensure_app_install_dir` Command

## Executive Summary

During the execution of the Smart Update routine via `manage-antigravity.sh update` (or selecting option `u` -> `[1] Everything` in the Antigravity Suite Manager Control Center), the update process aborted abruptly immediately following pre-update inspection:
```
/home/reza/.antigravity-suite-manager/bin/lib/sh/suite_update_detect.sh: line 16: ensure_app_install_dir: command not found
```

Investigation traced the issue to an orphaned function reference resulting from the elimination of the legacy F5 reload patch in commit `1108376`.

---

## Detailed Root Cause Analysis

### 1. Orphaned Shell Function Reference
Historically, `ensure_app_install_dir` was defined in `bin/lib/sh/patch_f5.sh` and `bin/lib/sh/patch_selector.sh`. Its role was to dynamically discover the active Antigravity Desktop App installation path containing `resources/app.asar` if `$APP_INSTALL_DIR` was unset or pointed to an unpopulated directory.

In commit `1108376` (`feat(cleanup): eliminate F5 reload patch and overhaul README with core features`), `bin/lib/sh/patch_f5.sh` was deleted. Concurrently, `patch_selector.sh` had previously been refactored into modular sub-scripts (`patch_selector_app.sh`, `patch_selector_helpers.sh`), which adopted the namespaced helper `ensure_selector_dirs`.

Consequently, no definition of `ensure_app_install_dir` remained anywhere in the repository, leaving four active consumers broken:
1. `bin/lib/sh/suite_update_detect.sh:16` (`detect_active_app_patches`)
2. `bin/lib/sh/patch_open_ide.sh:33` (`patch_open_ide_app`)
3. `bin/lib/sh/unpatch_open_ide.sh:11` (`unpatch_open_ide_app`)
4. `bin/lib/sh/uninstall_app.sh:25` (`uninstall_app`)

### 2. IDE Directory Detection Coupling
In `bin/lib/sh/suite_update_detect.sh`, `detect_active_ide_patches` called `ensure_rtl_dirs` from `patch_rtl_helpers.sh` as an ad-hoc mechanism to resolve `$IDE_INSTALL_DIR`. This introduced unnecessary cross-module coupling to RTL patch helpers for generic update orchestration.

---

## Technical Remediation

### 1. Centralized Installation Directory Resolution in `detect.sh`
Added standardized, self-contained `ensure_app_install_dir` and `ensure_ide_install_dir` functions to `bin/lib/sh/detect.sh`. Because `detect.sh` is loaded near the beginning of `manage-antigravity.sh` (alphabetical order `D`), these functions are guaranteed to be in scope for all subsequent update, patch, and uninstall modules:

```bash
ensure_app_install_dir() {
    [ -n "$APP_INSTALL_DIR" ] && [ -f "${APP_INSTALL_DIR}/resources/app.asar" ] && return 0
    auto_detect_installations 2>/dev/null || true
    [ -n "$APP_INSTALL_DIR" ] && [ -f "${APP_INSTALL_DIR}/resources/app.asar" ] && return 0
    for c in "$APP_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_APP" "/opt/Antigravity-x64" "/opt/antigravity2" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity"; do
        [ -n "$c" ] && [ -f "${c}/resources/app.asar" ] && { APP_INSTALL_DIR="$c"; return 0; }
    done
}

ensure_ide_install_dir() {
    [ -n "$IDE_INSTALL_DIR" ] && [ -d "${IDE_INSTALL_DIR}/resources/app/out" ] && return 0
    auto_detect_installations 2>/dev/null || true
    [ -n "$IDE_INSTALL_DIR" ] && [ -d "${IDE_INSTALL_DIR}/resources/app/out" ] && return 0
    for c in "$IDE_INSTALL_DIR" "$ANTIGRAVITY_DETECTED_IDE" "/opt/antigravity-ide" "/opt/antigravity" "${REAL_HOME:-$HOME}/.local/share/antigravity-ide"; do
        [ -n "$c" ] && [ -d "${c}/resources/app/out" ] && { IDE_INSTALL_DIR="$c"; return 0; }
    done
}
```

### 2. Decoupled IDE Patch Detection
Updated `detect_active_ide_patches` in `bin/lib/sh/suite_update_detect.sh` to use `ensure_ide_install_dir`:
```bash
detect_active_ide_patches() {
    ensure_ide_install_dir 2>/dev/null || ensure_rtl_dirs 2>/dev/null || true
    ...
```

### 3. Automated Regression Verification
Added `test_ensure_install_dirs_exist` to `tests/test_bash_features.py` to prevent regression during future cleanups. All 247 suite unit tests and JS router test suites pass cleanly.
