"""
Antigravity detection package exposing all installation inspection and configuration APIs.
"""

from __future__ import annotations

from antigravity_suite.detect.cli import main
from antigravity_suite.detect.clones_scan import scan_clones
from antigravity_suite.detect.configure_clone import configure_single_clone
from antigravity_suite.detect.configure_install import configure_single_installation
from antigravity_suite.detect.configure_paths import configure_paths_interactive
from antigravity_suite.detect.configure_unified import configure_unified_instance
from antigravity_suite.detect.control_center import run_control_center
from antigravity_suite.detect.history_helpers import copy_sqlite_db_safely, get_db_step_count
from antigravity_suite.detect.history_toggle import safe_toggle_history_mode
from antigravity_suite.detect.inspectors import inspect_app_dir, inspect_ide_dir
from antigravity_suite.detect.launchers import (
    create_launcher_and_desktop,
    get_launcher_binary,
    toggle_keyring_for_path,
    update_launcher_binary,
    update_launcher_profile_path,
)
from antigravity_suite.detect.paths_config import load_paths_config, save_paths_config
from antigravity_suite.detect.process import get_running_paths, is_acc1_running, is_main_ide_running
from antigravity_suite.detect.scan import print_table, scan_installations
from antigravity_suite.detect.unified import get_unified_instances

__all__ = [
    "main",
    "scan_installations",
    "print_table",
    "scan_clones",
    "load_paths_config",
    "save_paths_config",
    "update_launcher_profile_path",
    "get_launcher_binary",
    "update_launcher_binary",
    "create_launcher_and_desktop",
    "toggle_keyring_for_path",
    "safe_toggle_history_mode",
    "get_unified_instances",
    "run_control_center",
    "configure_paths_interactive",
    "configure_single_installation",
    "configure_single_clone",
    "configure_unified_instance",
    "is_acc1_running",
    "is_main_ide_running",
    "inspect_app_dir",
    "inspect_ide_dir",
    "get_running_paths",
    "get_db_step_count",
    "copy_sqlite_db_safely",
]
