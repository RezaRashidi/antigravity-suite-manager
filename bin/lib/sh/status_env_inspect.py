"""
Environment, keyring, sharing, and cache status checkers.
"""

from __future__ import annotations

import glob
import os
from typing import List, Tuple

try:
    from bin.lib.sh.status_inspect import G, NC, R, Y, get_app_version, get_ide_version
except ImportError:
    from status_inspect import G, NC, R, Y, get_app_version, get_ide_version


def check_keyring_storage(real_home: str, local_bin: str, profile2_dir: str) -> str:
    app1_cache = os.path.isfile(os.path.join(real_home, ".gemini", "cache", "antigravity-keyring-unavailable"))
    app1_l = os.path.join(local_bin, "antigravity-1")
    app1_flag = False
    if os.path.isfile(app1_l):
        try:
            with open(app1_l, "r", errors="ignore") as f: app1_flag = "--password-store=basic" in f.read()
        except Exception: pass
    app1_norm = (app1_cache or app1_flag)
    app2_lnch = os.path.join(local_bin, "antigravity-acc2")
    app2_exists = os.path.isdir(profile2_dir) and (os.path.isfile(app2_lnch) or os.path.islink(os.path.join(profile2_dir, ".gemini", "antigravity")))
    app2_norm = os.path.isfile(os.path.join(profile2_dir, ".gemini", "cache", "antigravity-keyring-unavailable"))

    if not app2_exists:
        return f"{G}Normal File Storage (Decoupled from GNOME Keyring){NC}" if app1_norm else f"{Y}GNOME Keyring (Secret Service){NC}"
    if app1_norm and app2_norm:
        return f"{G}Normal File Storage (Decoupled from GNOME Keyring){NC}"
    return f"{Y}Partial (Mixed File / Keyring){NC}" if (app1_norm or app2_norm) else f"{Y}GNOME Keyring (Secret Service){NC}"


def check_account2(profile2_dir: str) -> str:
    c = os.path.islink(os.path.join(profile2_dir, '.gemini', 'antigravity')) if profile2_dir else False
    if not profile2_dir or not os.path.isdir(profile2_dir) or not c:
        return f"{Y}Not Configured (Standalone profile 1){NC}"
    k = os.path.isfile(os.path.join(profile2_dir, '.gemini', 'cache', 'antigravity-keyring-unavailable'))
    f = os.path.exists(os.path.join(profile2_dir, '.gemini', 'config'))
    return f"{G}Configured (Isolated Keyring + Shared History){NC}" if (k and f) else f"{Y}Incomplete Setup{NC}"


def check_history_sharing(profile2_dir: str) -> str:
    rg = os.path.join(os.path.dirname(profile2_dir), '.gemini')
    ide_s, p2_s = os.path.islink(os.path.join(rg, 'antigravity-ide', 'conversations')), os.path.islink(os.path.join(profile2_dir, '.gemini', 'antigravity'))
    if ide_s and p2_s: return f"{G}3-Way Unified (App 1, App 2, IDE){NC}"
    return f"{Y}2-Way (App 1 & App 2 only){NC}" if p2_s else f"{R}Not Shared{NC}"


def check_customization_sharing(profile2_dir: str) -> str:
    gemide = os.path.join(os.path.dirname(profile2_dir), '.gemide')
    g_rule, g_cfg = os.path.islink(os.path.join(gemide, 'GEMINI.md')), os.path.islink(os.path.join(gemide, 'config'))
    p2_rule = os.path.islink(os.path.join(profile2_dir, '.gemini', 'GEMINI.md'))
    if g_rule and g_cfg and p2_rule: return f"{G}Unified (Rules, Skills, MCP across all instances){NC}"
    return f"{Y}Partially Shared{NC}" if (g_rule or p2_rule) else f"{Y}Standalone{NC}"


def check_write(d: str, real_user: str) -> str:
    if not os.path.isdir(d): return f"{R}Directory Missing{NC}"
    res = os.path.join(d, 'resources')
    w_d = os.access(d, os.W_OK)
    w_r = os.access(res, os.W_OK) if os.path.isdir(res) else False
    return f"{G}Writable by {real_user} (Ready){NC}" if (w_d and w_r) else f"{R}Read-Only for {real_user} (Requires fix_permissions){NC}"


def check_cached(cache_dir: str, name: str, ver: str) -> str:
    p = os.path.join(cache_dir, f"{name}-{ver}.tar.gz")
    if os.path.isfile(p) and os.path.getsize(p) > 10 * 1024 * 1024:
        return f"{G}Cached ({os.path.getsize(p) / (1024 * 1024):.1f} MB){NC}"
    return f"{Y}Not Cached (Download on demand){NC}"


def scan_all_installations() -> List[Tuple[str, str, str]]:
    cands: set[str] = set()
    roots = ['/opt', '/usr/share', '/usr/lib', '/usr/local/share', os.path.expanduser('~/.local/share'), os.path.expanduser('~/.local/lib'), os.path.expanduser('~/opt'), os.path.expanduser('~/.antigravity')]
    for r in roots:
        if os.path.isdir(r):
            for pat in ['*antigravity*', '*Antigravity*']:
                for m in glob.glob(os.path.join(r, pat)):
                    if os.path.isdir(m): cands.add(os.path.realpath(m))
    for p in os.environ.get('PATH', '').split(':'):
        for cmd in ['antigravity', 'antigravity-ide', 'antigravity-1', 'antigravity-acc2']:
            fp = os.path.join(p, cmd)
            if os.path.isfile(fp):
                d = os.path.dirname(os.path.realpath(fp))
                if 'manager' not in d.lower(): cands.add(d)
                if os.path.basename(d) in ['bin', 'MacOS']: cands.add(os.path.dirname(d))
    results, seen = [], set()
    for c in sorted(cands):
        rc = os.path.realpath(c)
        if rc in seen or 'manager' in rc.lower(): continue
        iv, av = get_ide_version(rc), get_app_version(rc)
        if iv: results.append(('Antigravity IDE', iv, rc)); seen.add(rc)
        elif av: results.append(('Antigravity App', av, rc)); seen.add(rc)
    return results
