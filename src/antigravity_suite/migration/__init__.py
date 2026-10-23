"""
Cross-System Migration and Backup Engine for Antigravity Suite.
"""

from antigravity_suite.cli.migration import build_parser, main
from antigravity_suite.migration.constants import (
    AGENTS_DIR,
    ANTIGRAVITY_CONF_DIR,
    BACKUPS_DIR,
    CONFIG_DIR,
    GEMINI_DIR,
    LOCAL_BIN,
    MASTER_GEMINI,
    REAL_HOME,
    REAL_USER,
    log_err,
    log_info,
    log_success,
    log_warn,
)
from antigravity_suite.migration.export_all import export_all
from antigravity_suite.migration.export_history import export_history
from antigravity_suite.migration.export_suite import export_suite
from antigravity_suite.migration.import_all import import_all
from antigravity_suite.migration.import_history import import_history, trigger_history_merge
from antigravity_suite.migration.import_suite import import_suite
from antigravity_suite.migration.mcp_merge import merge_mcp_configs
from antigravity_suite.migration.cleanup import (
    delete_all_data,
    delete_app_data,
    delete_history_data,
    delete_ide_data,
)
from antigravity_suite.migration.restore import restore_backup
from antigravity_suite.migration.restore_handlers import (
    restore_app_files,
    restore_history_files,
    restore_ide_files,
    restore_suite_files,
)
from antigravity_suite.migration.safety import create_safety_backup, list_all_backups
from antigravity_suite.migration.tar_utils import (
    add_path_safe,
    format_size,
    get_db_step_count,
    get_timestamp,
    safe_extract_tar,
)

__all__ = [
    "REAL_USER", "REAL_HOME", "GEMINI_DIR", "MASTER_GEMINI", "CONFIG_DIR",
    "AGENTS_DIR", "ANTIGRAVITY_CONF_DIR", "BACKUPS_DIR", "LOCAL_BIN",
    "log_info", "log_success", "log_warn", "log_err", "get_timestamp",
    "format_size", "safe_extract_tar", "get_db_step_count", "add_path_safe",
    "create_safety_backup", "list_all_backups", "restore_backup",
    "restore_history_files", "restore_suite_files", "restore_app_files", "restore_ide_files",
    "delete_app_data", "delete_ide_data", "delete_history_data", "delete_all_data",
    "export_history",
    "export_suite", "export_all", "trigger_history_merge", "import_history",
    "merge_mcp_configs", "import_suite", "import_all", "build_parser", "main",
]
