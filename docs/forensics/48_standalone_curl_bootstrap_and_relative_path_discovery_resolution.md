# Forensic Analysis Case 48: Standalone Curl Bootstrap Failure and Module Relative Path Discovery Regression

## Executive Summary
On fresh workstations or uninstalled instances, two distinct execution failures were encountered during setup and binary deployment:
1. Piped bootstrap execution via `curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash` failed with:
   `Error: manage-antigravity.sh not found.`
2. Running `install.sh` from an extracted release archive (e.g. `/home/reza/Downloads/antigravity-suite-manager-main/install.sh`) and selecting Option `[N]` (Install New Binary) in the Control Center failed with:
   `bash: /home/reza/Downloads/antigravity-suite-manager-main/src/bin/manage-antigravity.sh: No such file or directory`

Both failures stemmed from path resolution assumptions:
- **Failure 1**: `install.sh` depended on sourcing an external helper file (`bin/lib/installer/bootstrap.sh`) to perform auto-bootstrapping, but that file does not exist locally when streaming `install.sh` over curl to bash.
- **Failure 2**: Following modularization into `src/antigravity_suite/detect/`, multiple Python modules used a 3-level directory traversal (`os.path.dirname(os.path.dirname(os.path.dirname(__file__)))`), which evaluated to `<repo>/src` instead of the 4-level repository root. Appending `"bin", "manage-antigravity.sh"` yielded the non-existent path `<repo>/src/bin/manage-antigravity.sh`.

---

## Technical Root Cause Analysis

### 1. Piped Curl Execution (`curl | bash`)
When `install.sh` was invoked via `curl -fsSL ... | bash`:
- `$BASH_SOURCE[0]` was evaluated as empty or stdin.
- `MANAGE_SH` evaluated against `$SCRIPT_DIR/bin/manage-antigravity.sh` and `$HOME/.local/bin/manage-antigravity.sh`, neither of which existed on a clean machine.
- `install.sh` checked `if [ -f "${LIB_INSTALLER_DIR}/bootstrap.sh" ]`.
- Because `LIB_INSTALLER_DIR` (`$SCRIPT_DIR/bin/lib/installer`) had not been fetched yet, the test evaluated to false. The script fell through to the exit check and emitted `Error: manage-antigravity.sh not found.`.

### 2. Deep Module Relative Traversal (`src/bin/manage-antigravity.sh`)
In the Control Center TUI (`src/antigravity_suite/detect/control_center.py`):
```python
def run_control_center() -> None:
    local_bin = os.path.join(REAL_HOME, ".local", "bin")
    manage_sh = os.path.join(local_bin, "manage-antigravity.sh")
    if not os.path.isfile(manage_sh):
        manage_sh = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bin", "manage-antigravity.sh")
```
Given `__file__ = /path/to/repo/src/antigravity_suite/detect/control_center.py`:
- `1st dirname`: `/path/to/repo/src/antigravity_suite/detect`
- `2nd dirname`: `/path/to/repo/src/antigravity_suite`
- `3rd dirname`: `/path/to/repo/src` (3 levels deep, stopping inside `src`)
- `os.path.join(..., "bin", "manage-antigravity.sh")` produced `/path/to/repo/src/bin/manage-antigravity.sh`.
The true repository root was 4 levels deep (`/path/to/repo`).

Identical 3-level patterns were replicated across `configure_install.py`, `configure_clone.py`, `configure_unified.py`, `history_toggle.py`, `clone_keyring_icon.py`, `control_center_data.py`, `launcher_writer.py`, `import_history.py`, `gen_masters.py`, and `prompt_test.py`.

---

## Architectural Remediation

### 1. Centralized Script & Root Resolution (`constants.py`)
Implemented two canonical functions in `antigravity_suite.detect.constants`:
- `get_suite_root_dir()`: Ascends 4 directory levels from `constants.py` to identify the repository root, verifying the presence of `bin/manage-antigravity.sh` or `install.sh`, with fallback to `~/.antigravity-suite-manager`.
- `get_bin_script(name: str)`: Seamlessly discovers binaries across `~/.local/bin/<name>`, `<repo_root>/bin/<name>`, and `<repo_root>/<name>`.

### 2. Standalone Self-Bootstrapping (`install.sh`)
Embedded the bootstrap routine directly in `install.sh` as an inline fallback:
- If `manage-antigravity.sh` is missing and `bootstrap.sh` is not locally accessible (curl pipe scenario), `install.sh` directly clones or downloads the suite into `~/.antigravity-suite-manager`, installs `bin/` executables to `~/.local/bin/`, copies master desktop icons, and execs `manage-antigravity.sh` with `/dev/tty` support.
- If `~/.antigravity-suite-manager/bin/manage-antigravity.sh` exists on disk, `install.sh` detects and leverages it immediately.

### 3. Verification & Safety Guarantees
- Added unit tests `test_bin_script_resolution_no_src_bin` and `test_install_sh_bootstrap_integrity` in `tests/test_fixes_validation.py`.
- Verified 100% test suite pass across all 222 unit tests with zero regressions.
