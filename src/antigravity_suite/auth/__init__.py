"""
Authentication and Credential Management Package for Antigravity Suite.
"""

from antigravity_suite.auth.keyring_apply import (
    apply_mode_for_app1,
    apply_mode_for_app2,
    apply_mode_for_ide,
    update_launcher_password_store,
)
from antigravity_suite.auth.keyring_clones import apply_mode_for_clones
from antigravity_suite.auth.keyring_conf import load_config, save_config
from antigravity_suite.auth.keyring_dbus import (
    get_dbus_secrets_service,
    get_token_from_keyring,
    list_keyring_items,
)
from antigravity_suite.auth.keyring_purge import purge_antigravity_from_keyring
from antigravity_suite.auth.keyring_status import inspect_status
from antigravity_suite.auth.token import refresh_ide_oauth_token

__all__ = [
    "refresh_ide_oauth_token",
    "load_config",
    "save_config",
    "get_dbus_secrets_service",
    "list_keyring_items",
    "get_token_from_keyring",
    "purge_antigravity_from_keyring",
    "update_launcher_password_store",
    "apply_mode_for_app1",
    "apply_mode_for_app2",
    "apply_mode_for_ide",
    "apply_mode_for_clones",
    "inspect_status",
]
