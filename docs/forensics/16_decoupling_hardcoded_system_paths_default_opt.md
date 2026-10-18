# Issue 15: Decoupling Hardcoded System Paths: Default `/opt/*`, Account 2 Profile, Chromium Tray Temp Cache

### Symptoms
* On non-standard Linux distributions or systems where Antigravity is installed in user-local directories (`~/.local/share/`, `/usr/local/`, `/var/lib/`), paths detection defaulted to hardcoded `/opt/` paths (`/opt/antigravity2`, `/opt/antigravity`, `/opt/Antigravity-x64`) unless manually overridden in `paths.conf`.
* Single-profile systems or systems with custom secondary profile paths experienced inaccurate status output or process kill mismatches due to hardcoded `~/.antigravity-profile2` and fixed pgrep regexes.
* On systems configuring custom `$TMPDIR`, `$XDG_RUNTIME_DIR`, `/run/user/<uid>`, or `/var/tmp`, live Chromium tray icon cache syncing failed because the glob was hardcoded to `/tmp/org.chromium.Chromium.*`.

### Root Cause
1. **Installation Paths Fallback**: `paths_config.py` and `detect.sh` relied on hardcoded `/opt` candidate lists before considering environment variables (`ANTIGRAVITY_APP_DIR`, `ANTIGRAVITY_IDE_DIR`).
2. **Hardcoded Secondary Profile Identity**: `account2_launcher.sh`, `env.sh`, and `status_env_inspect.py` assumed `~/.antigravity-profile2` as the only secondary profile and used hardcoded regex patterns for process management.
3. **Hardcoded Temp Root**: `tray_sync.py` scanned strictly `/tmp`, ignoring standard temp resolution mechanisms like `tempfile.gettempdir()` and environment variables.

### Solution Applied
1. **Dynamic Installation Directory Resolution**:
   * Updated [paths_config.py](src/antigravity_suite/detect/paths_config.py) to prioritize `ANTIGRAVITY_APP_DIR` and `ANTIGRAVITY_IDE_DIR` over static defaults, followed by `paths.conf`, `scan_installations()`, and standard fallback candidate directories.
   * Updated [detect.sh](bin/lib/sh/detect.sh) to inspect `ANTIGRAVITY_APP_DIR`, `ANTIGRAVITY_IDE_DIR`, `ANTIGRAVITY_DETECTED_APP`, `ANTIGRAVITY_DETECTED_IDE`, and user-local share paths before `/opt`.
   * Updated [gen_masters.py](src/antigravity_suite/icon/gen_masters.py) to check active `app_dir/resources/icon.png` and `ide_dir/resources/app/resources/linux/code.png` before static fallbacks.
2. **Configurable Profile 2 Discovery & Resilient Single-Profile Support**:
   * In [bin/lib/sh/env.sh](bin/lib/sh/env.sh) and [bin/lib/installer/env.sh](bin/lib/installer/env.sh): Configured `PROFILE2_DIR="${ANTIGRAVITY_PROFILE2_DIR:-${PROFILE2_DIR:-${REAL_HOME}/.antigravity-profile2}}"`.
   * In [config_paths.py](src/antigravity_suite/config_paths.py) and [projects_roots.py](src/antigravity_suite/history/projects_roots.py): Dynamically resolve candidate Gemini directories by inspecting `ANTIGRAVITY_PROFILE2_DIR`.
   * In [account2_launcher.sh](bin/lib/sh/account2_launcher.sh): Replaced hardcoded pkill/pgrep regex with `user-data-dir=.*${PROFILE2}` and `class=antigravity-2`.
   * In [status_env_inspect.py](bin/lib/sh/status_env_inspect.py): Guarded `profile2_dir` checks with existence verification, cleanly supporting single-profile systems.
3. **Multi-Directory Chromium Tray Cache Resolution**:
   * In [tray_sync.py](src/antigravity_suite/icon/tray_sync.py): Implemented `_get_temp_dirs()` resolving `tempfile.gettempdir()`, `$TMPDIR`, `$XDG_RUNTIME_DIR`, `/run/user/<uid>`, `/tmp`, and `/var/tmp`.
   * Generalized process command line matching for Account 1 vs Account 2 across arbitrary profile directories.
4. **Validation & Regression Suite**:
   * Added unit tests in [test_fixes_validation.py](tests/test_fixes_validation.py): `test_tray_sync_dynamic_temp_dirs`, `test_dynamic_app_ide_env_paths_config`, `test_dynamic_profile2_env_discovery`.
   * Full test suite verification: 117/117 unit tests passing.

---
