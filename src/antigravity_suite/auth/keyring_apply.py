"""
Keyring storage mode enforcement for App1, App2, and IDE.
"""

from __future__ import annotations

import os
import re
from antigravity_suite.auth.keyring_constants import GREEN, LOCAL_BIN, NC, PROFILE2_DIR, REAL_HOME
from antigravity_suite.auth.keyring_dbus import get_token_from_keyring


def update_launcher_password_store(launcher_path: str, mode: str) -> None:
    """Updates the --password-store flag in an instance launcher script."""
    if not os.path.isfile(launcher_path):
        return
    with open(launcher_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_lines = []
    for line in content.splitlines():
        if line.strip().startswith("exec "):
            if mode == "normal" and "--password-store=basic" not in line:
                m = re.match(r'^(\s*exec\s+("[^"]+"|\'[^\']+\'|\S+))(.*)$', line)
                if m:
                    line = f'{m.group(1)} --password-store=basic{m.group(3)}'
            elif mode == "gnome":
                line = line.replace("--password-store=basic ", "").replace("--password-store=basic", "")
        new_lines.append(line)

    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")
    os.chmod(launcher_path, 0o755)


def _apply_app_mode(cache_file: str, token_file: str, launcher: str, mode: str, migrate_token: bool, name: str) -> None:
    if mode == "normal":
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "a"):
            os.utime(cache_file, None)
        if migrate_token and not os.path.isfile(token_file):
            t_data = get_token_from_keyring()
            if t_data:
                os.makedirs(os.path.dirname(token_file), exist_ok=True)
                with open(token_file, "w", encoding="utf-8") as f:
                    f.write(t_data)
                os.chmod(token_file, 0o600)
                print(f"{GREEN}[MIGRATED]{NC} Saved {name} login token to {token_file}")
        update_launcher_password_store(launcher, "normal")
    else:
        if os.path.isfile(cache_file):
            try: os.remove(cache_file)
            except Exception: pass
        update_launcher_password_store(launcher, "gnome")


def apply_mode_for_app1(mode: str, migrate_token: bool = True) -> None:
    """Configures keyring mode for Primary App."""
    has_acc2 = os.path.isfile(os.path.join(LOCAL_BIN, "antigravity-acc2")) and os.path.isdir(PROFILE2_DIR)
    name = "Account 1" if has_acc2 else "Antigravity App"
    lnch = os.path.join(LOCAL_BIN, "antigravity" if not has_acc2 else "antigravity-1")
    if not os.path.isfile(lnch) and os.path.isfile(os.path.join(LOCAL_BIN, "antigravity-1")):
        lnch = os.path.join(LOCAL_BIN, "antigravity-1")
    _apply_app_mode(
        os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable"),
        os.path.join(REAL_HOME, ".gemini", "jetski-standalone-oauth-token"),
        lnch, mode, migrate_token, name,
    )


def apply_mode_for_app2(mode: str, migrate_token: bool = True) -> None:
    """Configures keyring mode for Account 2 desktop app."""
    lnch = os.path.join(LOCAL_BIN, "antigravity-acc2")
    if not os.path.isfile(lnch) and not os.path.islink(os.path.join(PROFILE2_DIR, ".gemini", "antigravity")):
        return
    _apply_app_mode(
        os.path.join(PROFILE2_DIR, ".gemini", "cache", "antigravity-keyring-unavailable"),
        os.path.join(PROFILE2_DIR, ".gemini", "jetski-standalone-oauth-token"),
        lnch, mode, migrate_token, "Account 2",
    )


def apply_mode_for_ide(mode: str) -> None:
    """Configures keyring mode for Antigravity IDE."""
    update_launcher_password_store(os.path.join(LOCAL_BIN, "antigravity-ide"), mode)
    ide_cache_files = [
        os.path.join(REAL_HOME, ".gemide", "cache", "antigravity-keyring-unavailable"),
        os.path.join(REAL_HOME, ".gemini", "antigravity-ide", "cache", "antigravity-keyring-unavailable"),
    ]
    for cf in ide_cache_files:
        if mode == "normal":
            try:
                os.makedirs(os.path.dirname(cf), exist_ok=True); open(cf, "a").close()
            except Exception: pass
        elif os.path.isfile(cf):
            try: os.remove(cf)
            except Exception: pass
