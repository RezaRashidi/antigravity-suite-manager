#!/usr/bin/env python3
"""
Antigravity Installation Detector & Suite Manager CLI.
"""

from __future__ import annotations

import os
import sys

_SRC_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "src"))
if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

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
