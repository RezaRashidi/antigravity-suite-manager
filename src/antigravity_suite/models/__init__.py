"""Antigravity custom models management core package."""

from __future__ import annotations

from antigravity_suite.models.config import (
    DEFAULT_CONFIG_FILENAME,
    get_custom_models_path,
    get_default_config,
    load_config,
    save_config,
)
from antigravity_suite.models.discovery import fetch_models, get_discovery_urls
from antigravity_suite.models.ide_adapter import (
    CLOUD_CODE_KEY,
    DEFAULT_CLOUD_CODE_URL,
    apply_ide_proxy_url,
    get_ide_backup_path,
    get_ide_proxy_url,
    get_ide_settings_path,
    restore_ide_proxy_url,
)
from antigravity_suite.models.parser import ModelInfo, parse_model_catalog
from antigravity_suite.models.proxy_daemon import (
    DEFAULT_PROXY_PORT,
    get_proxy_pid,
    get_proxy_pid_path,
    get_proxy_status,
    is_proxy_running,
    start_proxy_daemon,
    stop_proxy_daemon,
)
from antigravity_suite.models.selector import (
    enable_all_models,
    enable_selected_models,
    make_standard_name,
    toggle_model,
)
from antigravity_suite.models.tester import test_model_endpoint

__all__ = [
    "DEFAULT_CONFIG_FILENAME",
    "get_custom_models_path",
    "get_default_config",
    "load_config",
    "save_config",
    "get_discovery_urls",
    "fetch_models",
    "ModelInfo",
    "parse_model_catalog",
    "make_standard_name",
    "enable_all_models",
    "enable_selected_models",
    "toggle_model",
    "test_model_endpoint",
    "DEFAULT_CLOUD_CODE_URL",
    "CLOUD_CODE_KEY",
    "get_ide_settings_path",
    "get_ide_backup_path",
    "apply_ide_proxy_url",
    "restore_ide_proxy_url",
    "get_ide_proxy_url",
    "DEFAULT_PROXY_PORT",
    "get_proxy_pid_path",
    "get_proxy_pid",
    "is_proxy_running",
    "get_proxy_status",
    "start_proxy_daemon",
    "stop_proxy_daemon",
]
