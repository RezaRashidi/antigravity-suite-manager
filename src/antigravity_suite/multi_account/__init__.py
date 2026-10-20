"""Antigravity Multi-Account Subsystem."""

from __future__ import annotations

from antigravity_suite.multi_account.bindings import (
    bind_cascade_to_account, get_account_for_cascade, load_bindings,
    unbind_cascade
)
from antigravity_suite.multi_account.models import (
    AccountRecord, AccountToken, ConversationBinding, QuotaBucket
)
from antigravity_suite.multi_account.oauth import start_login_flow
from antigravity_suite.multi_account.proxy_core import (
    DEFAULT_UPSTREAM, extract_cascade_id, prepare_upstream_headers,
    resolve_account_token
)
from antigravity_suite.multi_account.proxy_server import (
    MultiAccountProxyHandler, run_proxy_server
)
from antigravity_suite.multi_account.quota import fetch_account_quotas, fetch_account_tier
from antigravity_suite.multi_account.service import (
    is_proxy_running, start_proxy_daemon, stop_proxy_daemon
)
from antigravity_suite.multi_account.tokens import (
    is_token_expired, parse_jwt_claims, refresh_access_token
)
from antigravity_suite.multi_account.vault import (
    list_vault_accounts, remove_account_from_vault, save_account_to_vault
)

__all__ = [
    "AccountRecord",
    "AccountToken",
    "ConversationBinding",
    "QuotaBucket",
    "bind_cascade_to_account",
    "extract_cascade_id",
    "fetch_account_quotas",
    "fetch_account_tier",
    "get_account_for_cascade",
    "is_proxy_running",
    "is_token_expired",
    "list_bindings",
    "list_vault_accounts",
    "load_bindings",
    "parse_jwt_claims",
    "prepare_upstream_headers",
    "refresh_access_token",
    "remove_account_from_vault",
    "resolve_account_token",
    "run_proxy_server",
    "save_account_to_vault",
    "start_login_flow",
    "start_proxy_daemon",
    "stop_proxy_daemon",
    "unbind_cascade",
]
