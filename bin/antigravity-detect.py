#!/usr/bin/env python3
"""
Antigravity Installation Detector & Suite Manager CLI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

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
for _c in _candidates:
    if _c and Path(_c).is_dir():
        _c_str = str(_c)
        if _c_str not in sys.path:
            sys.path.insert(0, _c_str)
        break

from antigravity_suite.detect import (
    configure_paths_interactive,
    configure_single_clone,
    configure_single_installation,
    configure_unified_instance,
    copy_sqlite_db_safely,
    create_launcher_and_desktop,
    get_db_step_count,
    get_launcher_binary,
    get_running_paths,
    get_unified_instances,
    inspect_app_dir,
    inspect_ide_dir,
    is_acc1_running,
    is_main_ide_running,
    load_paths_config,
    main,
    print_table,
    run_control_center,
    safe_toggle_history_mode,
    save_paths_config,
    scan_clones,
    scan_installations,
    toggle_keyring_for_path,
    update_launcher_binary,
    update_launcher_profile_path,
)

if __name__ == "__main__":
    main()
