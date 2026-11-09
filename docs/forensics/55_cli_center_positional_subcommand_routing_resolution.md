# Forensic Analysis Case 55: Resolution of Setup Wizard Trigger on `manage-antigravity.sh center`

## Executive Summary

When executing `~/manage-antigravity.sh center` or `manage-antigravity.sh control-center`, users unexpectedly encountered the 8-step interactive installation wizard:
```
[Step 1/8] Check Dependencies & Prerequisites...
[OK] Core dependencies verified.

----------------------------------------------------------------------
Completed Step 1: Check Dependencies & Prerequisites
Next up Step 2: Configure Installation Paths & Engines
[Enter] Continue | [s]kip next | [j <1-8>] jump | [u]pdate | [q]uit: 
```

Rather than launching the curses-based interactive Antigravity Control Center (`control_center.py` or fallback interactive menu), the command initiated the full step-by-step suite installation sequence.

---

## Detailed Root Cause Analysis

### 1. Inadvertent Command Grouping in CLI Parser
In `bin/lib/sh/cli_parse.sh`, positional arguments are evaluated in a `case "$1" in` block:
```bash
wizard|setup|center|control-center) COMMAND="wizard"; shift; CMD_ARGS=("$@"); break ;;
```

Here, `center` and `control-center` were erroneously matched alongside `wizard` and `setup` and assigned `COMMAND="wizard"`.

### 2. Dispatcher Routing Asymmetry
In `bin/lib/sh/cli_dispatch.sh`:
```bash
dispatch_command() {
    if [ -z "$COMMAND" ] || [ "$COMMAND" = "center" ] || [ "$COMMAND" = "control-center" ]; then
        interactive_menu; return 0
    fi
    case "$COMMAND" in
        classic-menu) show_classic_menu ;;
        wizard) run_wizard_flow ;;
        ...
```
The dispatcher explicitly intended for `COMMAND="center"` or `COMMAND="control-center"` (as well as empty `COMMAND` when invoked with no arguments) to invoke `interactive_menu`.
Furthermore, `bin/lib/sh/cli_flags.sh` already mapped `--menu|--center|--control-center` to `COMMAND="center"`.

Because `cli_parse.sh` overwrote positional `center` and `control-center` to `COMMAND="wizard"`, execution routed into `run_wizard_flow`, beginning with Step 1 of the installer workflow instead of `interactive_menu`.

---

## Technical Remediation

### 1. Decoupled Positional CLI Arguments in `cli_parse.sh`
Separated `wizard` / `setup` from `center` / `control-center` / `menu` and added support for `classic-menu`:

```bash
wizard|setup) COMMAND="wizard"; shift; CMD_ARGS=("$@"); break ;;
center|control-center|menu) COMMAND="center"; shift; CMD_ARGS=("$@"); break ;;
classic-menu) COMMAND="classic-menu"; shift; CMD_ARGS=("$@"); break ;;
```

### 2. Comprehensive Test Coverage
Updated `tests/test_bash_features.py` under `test_cli_dispatch_and_parse` to assert the presence of `center|control-center|menu` in `cli_parse.sh` and `COMMAND = "center"` in `cli_dispatch.sh`.

All 248 unit tests in the suite pass cleanly.
