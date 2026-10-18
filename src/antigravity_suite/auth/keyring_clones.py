"""
Keyring storage mode enforcement for profile clones.
"""

from __future__ import annotations

import glob
import os
from antigravity_suite.auth.keyring_apply import update_launcher_password_store
from antigravity_suite.auth.keyring_constants import GREEN, LOCAL_BIN, NC, REAL_HOME


def apply_mode_for_clones(mode_normalized: str) -> None:
    """Applies keyring mode to custom profile clone launchers and cache files."""
    for p in sorted(glob.glob(os.path.join(REAL_HOME, '.antigravity-profile-app-*'))):
        if '.bak' in p or '.removed' in p:
            continue
        cname = os.path.basename(p).replace('.antigravity-profile-app-', '')
        c_cache = os.path.join(p, '.gemini', 'cache', 'antigravity-keyring-unavailable')
        c_launcher = os.path.join(LOCAL_BIN, f'antigravity-app-{cname}')
        if not os.path.isfile(c_launcher):
            alt_l = os.path.join(LOCAL_BIN, f'antigravity-{cname}')
            if os.path.isfile(alt_l):
                c_launcher = alt_l
        if mode_normalized == "normal":
            os.makedirs(os.path.dirname(c_cache), exist_ok=True)
            with open(c_cache, "a"):
                os.utime(c_cache, None)
            update_launcher_password_store(c_launcher, "normal")
        else:
            if os.path.isfile(c_cache):
                try: os.remove(c_cache)
                except Exception: pass
            update_launcher_password_store(c_launcher, "gnome")
        print(f"{GREEN}[OK]{NC} Switched App Clone '{cname}' to {mode_normalized.upper()} mode.")

    for p in sorted(glob.glob(os.path.join(REAL_HOME, '.antigravity-ide-profile-*'))):
        if '.bak' in p or '.removed' in p:
            continue
        cname = os.path.basename(p).replace('.antigravity-ide-profile-', '')
        c_launcher = os.path.join(LOCAL_BIN, f'antigravity-ide-{cname}')
        ide_caches = [
            os.path.join(p, '.gemide', 'cache', 'antigravity-keyring-unavailable'),
            os.path.join(p, '.gemini', 'antigravity-ide', 'cache', 'antigravity-keyring-unavailable')
        ]
        for cf in ide_caches:
            if mode_normalized == "normal":
                try:
                    os.makedirs(os.path.dirname(cf), exist_ok=True)
                    with open(cf, "a"): os.utime(cf, None)
                except Exception: pass
            elif os.path.isfile(cf):
                try: os.remove(cf)
                except Exception: pass
        update_launcher_password_store(c_launcher, mode_normalized)
        print(f"{GREEN}[OK]{NC} Switched IDE Clone '{cname}' to {mode_normalized.upper()} mode.")
