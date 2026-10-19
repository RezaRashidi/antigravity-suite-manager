# Issue 21: Self-Update Engine & Background Service Orchestration

## 1. Problem Statement
The user requested mechanisms to:
1. Self-update the `antigravity-suite-manager` repository itself (pulling latest commits, recompiling binaries, redeploying scripts, refreshing Python package bindings).
2. Cleanly restart background daemon services without blocking interactive shells or leaving stale daemons running.

## 2. Root Cause Analysis & Architecture Design
1. **Self-Update Workflow**:
   - Repository location must be discovered regardless of invocation context (`manage-antigravity.sh` run from `~/.local/bin`, `~/manage-antigravity.sh`, or git checkout).
   - Python module metadata (`antigravity_suite.__file__`) provides unambiguous discovery when invoked outside the repo tree.
   - Self-update must recompile the C Catmull-Rom resampler (`scale_icon.c`), redeploy all scripts in `bin/` and sub-libraries in `bin/lib/` to `~/.local/bin`, refresh `antigravity_suite.pth` in Python user site-packages, and trigger automatic background service restarts.

2. **Non-Blocking Service Orchestration**:
   - `systemctl --user restart antigravity-sync.service` blocks until graceful stop/start completes. Supplying `--no-block` ensures instantaneous queuing without shell freezing.
   - `antigravity-apply-icon.py --daemon` executes a 30-second window poll loop. Standard background launching (`&`) can keep standard streams open in child subshells. Decoupling with `nohup` and stdin redirection (`</dev/null >/dev/null 2>&1 &`) ensures instant detached execution.

## 3. Implementation
- **Repository Self-Update**: Implemented `update_suite_repo()` and `find_suite_repo_root()` in `bin/lib/sh/repo_update.sh`.
- **Service Orchestration**: Implemented `restart_suite_services()` in `bin/lib/sh/sync_service.sh`.
- **CLI & Dispatch Wiring**: Added `update-repo`, `update self`, `update repo`, `restart-services`, and `update services` across `bin/lib/sh/cli_parse.sh`, `cli_dispatch.sh`, `cli_dispatch_helpers.sh`, and `help.sh`.
- **Installer Integration**: Added `--update-repo` and `--restart-services` flags to `bin/lib/installer/cli.sh` and `runner.sh`.
- **Interactive Interfaces**: Added entries 24 and 25 to `bin/lib/sh/menu.sh` and shortcuts `[P]` (Update Repo) & `[D]` (Restart Services) to `control_center.py`.
