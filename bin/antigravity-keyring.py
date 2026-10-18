#!/usr/bin/env python3
"""
Antigravity Keyring & Credential Manager CLI Entry Point.
"""

# Reference: attrs.get('service') == 'gemini' and 'antigravity' in attrs.get('username'
from __future__ import annotations

import os
import sys
from pathlib import Path

_cur = Path(__file__).resolve().parent
_candidates = [
    os.environ.get("ANTIGRAVITY_SUITE_DIR") and Path(os.environ["ANTIGRAVITY_SUITE_DIR"]) / "src",
    _cur.parent / "src",
    Path.home() / ".antigravity-suite-manager" / "src",
    Path.home() / "PhpstormProjects" / "antigravity-suite-manager" / "src",
    Path.cwd() / "src",
]
for _c in _candidates:
    if _c and Path(_c).is_dir() and str(_c) not in sys.path:
        sys.path.insert(0, str(_c))

from antigravity_suite.auth import *
from antigravity_suite.cli.keyring import build_parser, handle_set, main

__all__ = [
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
    "build_parser",
    "handle_set",
    "main",
]

if __name__ == "__main__":
    sys.exit(main())
