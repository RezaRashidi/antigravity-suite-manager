"""
Facade for Control Center action handlers.
"""

from __future__ import annotations

from antigravity_suite.detect.control_center_data import (
    handle_control_center_backups,
    handle_control_center_clean_data,
    handle_control_center_export_import,
    handle_control_center_uninstall,
)
from antigravity_suite.detect.control_center_launch import (
    handle_control_center_clone,
    handle_control_center_install,
    handle_control_center_launch,
    handle_control_center_steps,
    handle_control_center_update,
)
from antigravity_suite.detect.control_center_ops import (
    handle_control_center_clean_cache,
    handle_control_center_icons,
    handle_control_center_keyring_global,
    handle_control_center_merge_history,
    handle_control_center_multi_account,
    handle_control_center_status,
    handle_control_center_traffic,
)
from antigravity_suite.detect.control_center_patches import (
    handle_control_center_f5_patch,
    handle_control_center_fork_patch,
    handle_control_center_models_patch,
    handle_control_center_open_ide_patch,
    handle_control_center_rtl_patch,
    handle_control_center_selector_patch,
)

__all__ = [
    "handle_control_center_backups",
    "handle_control_center_clean_cache",
    "handle_control_center_clean_data",
    "handle_control_center_clone",
    "handle_control_center_export_import",
    "handle_control_center_f5_patch",
    "handle_control_center_fork_patch",
    "handle_control_center_icons",
    "handle_control_center_install",
    "handle_control_center_keyring_global",
    "handle_control_center_launch",
    "handle_control_center_merge_history",
    "handle_control_center_models_patch",
    "handle_control_center_multi_account",
    "handle_control_center_open_ide_patch",
    "handle_control_center_rtl_patch",
    "handle_control_center_selector_patch",
    "handle_control_center_status",
    "handle_control_center_steps",
    "handle_control_center_traffic",
    "handle_control_center_uninstall",
    "handle_control_center_update",
]
