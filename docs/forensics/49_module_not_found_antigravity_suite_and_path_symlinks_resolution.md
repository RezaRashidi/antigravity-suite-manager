# Forensic Analysis Case 49: ModuleNotFoundError: No module named 'antigravity_suite' on Repeated Install & System PATH Symlinks

## Executive Summary
When running `install.sh` for the second time on secondary workstations via:
```bash
curl -fsSL https://raw.githubusercontent.com/RezaRashidi/antigravity-suite-manager/main/install.sh | bash
```
Execution failed with the following traceback:
```
Traceback (most recent call last):
  File "/home/reza/.local/bin/antigravity-detect.py", line 15, in <module>
    from antigravity_suite.detect import (
ModuleNotFoundError: No module named 'antigravity_suite'
```
Simultaneously, the operator requested persistent `$PATH` integration so that management commands (`manage-antigravity`, `antigravity-suite`) can be invoked from any terminal prompt without manual prefixing.

---

## Technical Root Cause Analysis

### 1. `ModuleNotFoundError: No module named 'antigravity_suite'`
1. **Shallow Script Copying**:
   The installer deployed executable CLI scripts from `bin/*` into `~/.local/bin/`. However, the Python package sources reside under `<repo>/src/antigravity_suite`.
2. **Deficient `sys.path` Resolution**:
   In `bin/antigravity-detect.py`, `bin/antigravity-benchmark.py`, and `bin/antigravity-multi-account.py`, the import path was statically hardcoded to:
   ```python
   _SRC_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "src"))
   if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
       sys.path.insert(0, _SRC_DIR)
   ```
   When invoked as `~/.local/bin/antigravity-detect.py`, `os.path.dirname(__file__)` evaluated to `~/.local/bin`, and `_SRC_DIR` evaluated to `~/.local/src` (which does not exist).
3. **Repeated Run Stale Execution**:
   On repeated execution of `curl ... | bash`, `install.sh` observed that `~/.local/bin/manage-antigravity.sh` already existed and immediately exec'd it without updating the codebase, without registering Python site-packages `.pth`, and without exporting `PYTHONPATH`.

---

## Architectural Remediation

### 1. Multi-Candidate Discovery Across Python CLIs
Updated `bin/antigravity-detect.py`, `bin/antigravity-benchmark.py`, and `bin/antigravity-multi-account.py` to inspect dynamic candidates:
```python
_cur = Path(__file__).resolve().parent
_real_home = os.environ.get("REAL_HOME") or str(Path.home())
_candidates = [
    os.environ.get("ANTIGRAVITY_SUITE_DIR") and Path(os.environ["ANTIGRAVITY_SUITE_DIR"]) / "src",
    _cur.parent / "src",
    Path(_real_home) / ".antigravity-suite-manager" / "src",
    Path.home() / ".antigravity-suite-manager" / "src",
    Path("/opt/antigravity-suite-manager/src"),
    Path.cwd() / "src",
]
```

### 2. Auto-Discovery & `PYTHONPATH` Export in Orchestrator
Updated `bin/manage-antigravity.sh` to auto-discover `ANTIGRAVITY_SUITE_DIR` and export `PYTHONPATH="${ANTIGRAVITY_SUITE_DIR}/src:$PYTHONPATH"` on invocation.

### 3. Comprehensive `setup_suite_env_and_links` in Installer
Enhanced `install.sh`, `bootstrap.sh`, `step_4.sh`, and `repo_update.sh`:
1. **Python `.pth` Registration**:
   Writes `<repo>/src` into `~/.local/lib/python3.x/site-packages/antigravity_suite.pth`.
2. **Management Executable Symlinks**:
   - `~/.local/bin/manage-antigravity` -> `manage-antigravity.sh`
   - `~/.local/bin/antigravity-suite` -> `manage-antigravity.sh`
   - `~/manage-antigravity` -> `manage-antigravity.sh`
   - `/usr/local/bin/manage-antigravity` (if writable or sudo available)
   - `/usr/local/bin/antigravity-suite`
3. **Persistent Shell `$PATH` Guarantee**:
   Inspects `~/.bashrc`, `~/.zshrc`, and `~/.profile` and appends `export PATH="${HOME}/.local/bin:${PATH}"` if not already present.
4. **Self-Updating Repeated Runs**:
   When invoked via `curl | bash` outside the repository, `install.sh` updates or clones `~/.antigravity-suite-manager`, redeploys scripts, updates symlinks, and executes the latest binary.

---

## Verification
- Added regression tests `test_direct_detect_py_standalone_resolution` and `test_install_sh_path_and_symlinks` in `tests/test_fixes_validation.py`.
- Verified 76 test cases passing in `test_fixes_validation.py` and all 224 unit tests passing across the entire test suite.
