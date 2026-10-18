"""
Keyring and credential status inspection across suite instances.
"""

from __future__ import annotations

import os
from antigravity_suite.auth.keyring_conf import load_config
from antigravity_suite.auth.keyring_constants import BLUE, BOLD, CYAN, GREEN, LOCAL_BIN, NC, PROFILE2_DIR, REAL_HOME, YELLOW
from antigravity_suite.auth.keyring_dbus import list_keyring_items


def _check_flag(launcher: str) -> bool:
    if os.path.isfile(launcher):
        with open(launcher, "r", errors="ignore") as f:
            return "--password-store=basic" in f.read()
    return False


def inspect_status() -> None:
    """Inspects and prints keyring and token status for App1, App2, and IDE."""
    load_config()
    print(f"{CYAN}{'='*88}{NC}\n{BOLD}{CYAN}{'Antigravity Credential & Keyring Status':^88}{NC}\n{CYAN}{'='*88}{NC}")

    app1_cache = os.path.isfile(os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable"))
    app1_token = os.path.isfile(os.path.join(REAL_HOME, ".gemini", "jetski-standalone-oauth-token"))
    app1_flag = _check_flag(os.path.join(LOCAL_BIN, "antigravity-1"))
    app1_state = f"{GREEN}Normal (Plain File / No Keyring){NC}" if (app1_cache or app1_flag) else f"{YELLOW}GNOME Keyring (Secret Service){NC}"

    app2_cache = os.path.isfile(os.path.join(PROFILE2_DIR, ".gemini", "cache", "antigravity-keyring-unavailable"))
    app2_token = os.path.isfile(os.path.join(PROFILE2_DIR, ".gemini", "jetski-standalone-oauth-token"))
    app2_flag = _check_flag(os.path.join(LOCAL_BIN, "antigravity-acc2"))
    app2_state = f"{GREEN}Normal (Plain File / No Keyring){NC}" if (app2_cache or app2_flag) else f"{YELLOW}GNOME Keyring (Secret Service){NC}"

    ide_flag = _check_flag(os.path.join(LOCAL_BIN, "antigravity-ide"))
    ide_cache = any(os.path.isfile(cf) for cf in [
        os.path.join(REAL_HOME, ".gemide", "cache", "antigravity-keyring-unavailable"),
        os.path.join(REAL_HOME, ".gemini", "antigravity-ide", "cache", "antigravity-keyring-unavailable"),
    ])
    ide_state = f"{GREEN}Normal (Plain File / No Keyring){NC}" if (ide_cache or ide_flag) else f"{YELLOW}GNOME Keyring (Secret Service){NC}"

    print(f"{BOLD}{BLUE}{'Instance':<22} {'Active Storage Mode':<44} {'Local Token File':<19} Flag (--password-store=basic){NC}")
    print("-" * 88)
    print(f"Antigravity (Acc 1)    {app1_state:<44} {'Yes (standalone)' if app1_token else 'Keyring only':<19} {'Active' if app1_flag else 'None'}")
    print(f"Antigravity (Acc 2)    {app2_state:<44} {'Yes (standalone)' if app2_token else 'Keyring only':<19} {'Active' if app2_flag else 'None'}")
    print(f"Antigravity IDE        {ide_state:<44} {'N/A (VS Code store)':<19} {'Active' if ide_flag else 'None'}")
    print("-" * 88)

    items = list_keyring_items()
    print(f"{BOLD}Items Currently Inside GNOME Keyring ({len(items)} found):{NC}")
    if items:
        for it in items:
            print(f"  • {it['label']} ({it['path']})")
            for k, v in it['attributes'].items():
                print(f"      {k}: {v}")
    else:
        print(f"  {GREEN}None (Antigravity is completely clear of GNOME Keyring){NC}")
    print(f"{CYAN}{'='*88}{NC}")
