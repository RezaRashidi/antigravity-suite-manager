# Forensic Report 21: Antigravity IDE Corruption Dialog & VS Code Checksum Integrity Synchronization

## Incident Summary
Users reported the following warning dialog on startup of Antigravity IDE:
> **"Your Antigravity IDE installation appears to be corrupt. Please reinstall."**

## Root Cause Analysis
Antigravity IDE is built on top of VS Code OSS. VS Code implements an internal `IntegrityService` (`workbench.desktop.main.js` / `IIntegrityService`) that executes during application startup.

### 1. Integrity Verification Flow
1. At build time, VS Code packages a manifest of expected SHA-256 base64 hashes for core bundle files inside `/opt/antigravity/resources/app/product.json` under `"checksums"` (11 tracked bundle files).
2. At runtime startup, `IntegrityService` reads each file in `product.json["checksums"]`, calculates its SHA-256 base64 digest (with trailing `=` padding stripped), and checks:
   ```javascript
   isPure: actual === expected
   ```
3. If ANY file hash diverges from `product.json`:
   - `isPure` evaluates to `false`.
   - The workbench invokes `_showNotification()` using NLS message index `15829`:
     `"Your {0} installation appears to be corrupt. Please reinstall."`

### 2. Forensic File Divergence
Inspection of `/opt/antigravity/resources/app/out/` revealed 3 files failed checksum checks:
1. `vs/workbench/workbench.desktop.main.js`
   - Modified by custom workbench patch injecting the UI refresh/sync button.
2. `vs/code/electron-browser/workbench/workbench.html`
   - Modified by `antigravity-rtl` injecting `data:` font-src CSP allowances.
3. `vs/code/electron-browser/workbench/workbench-jetski-agent.html`
   - Modified by `antigravity-rtl` injecting `data:` font-src CSP allowances.

Because `antigravity-rtl` and custom bundle patches did not recalculate the hashes in `product.json`, the IDE flagged the installation as corrupted on every startup.

## Permanent Remediation
1. **Patcher Core Library (`src/antigravity_suite/patch/ide_checksums.py`)**:
   - `compute_file_checksum()`: Implements VS Code's exact streaming SHA-256 base64 unpadded hash algorithm.
   - `verify_ide_checksums()`: Inspects all files in `product.json["checksums"]` and returns match statuses.
   - `sync_ide_checksums()`: Recomputes hashes of all modified bundle files and atomically rewrites `product.json`.
2. **CLI Entrypoint (`bin/antigravity-checksums.py`)**:
   - Added standalone executable with `--verify` and auto-sync modes, installed to `~/.local/bin/antigravity-checksums`.
3. **Automated Hook Integration (`bin/lib/sh/patch_rtl.sh`)**:
   - `patch_rtl_ide` and `update_rtl` now automatically invoke `fix_ide_checksums` immediately after modifying workbench files.
   - CLI dispatch exposes `antigravity-suite-manager checksums` / `fix-checksums`.
4. **Verification**:
   - All 11 files verified as `[OK]`.
   - Unit test suite added in `tests/test_ide_checksums.py` (all 123 tests pass).
