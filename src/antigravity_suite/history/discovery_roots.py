"""
Candidate Home Directories, Profile Roots, and Desktop Launcher Discovery.
"""

from __future__ import annotations

import getpass
import glob
import os
import re
from pathlib import Path
from typing import List, Optional, Set, Union

from antigravity_suite.config import get_user_home


def get_candidate_homes(user_home: Optional[Union[str, Path]] = None) -> Set[str]:
    """Collect candidate user home directories."""
    effective_home = str(user_home) if user_home else str(get_user_home())
    homes: Set[str] = set()
    if effective_home:
        homes.add(effective_home)
        if ".antigravity-profile" in effective_home:
            homes.add(os.path.dirname(effective_home))
    real_env = os.environ.get("REAL_HOME")
    if real_env:
        homes.add(real_env)
    homes.add(os.path.expanduser("~"))
    try:
        user = os.environ.get("USER") or getpass.getuser()
        homes.add(os.path.expanduser(f"~{user}"))
    except Exception:
        pass
    return homes


def get_profile_search_roots(homes: Set[str]) -> Set[str]:
    """Collect candidate profile and data roots across discovered homes."""
    roots: Set[str] = set()
    for h in homes:
        if not os.path.isdir(h):
            continue
        for sub in [".gemini", ".gemini-ide", ".gemide", ".config/Antigravity", ".config/Antigravity IDE",
                    ".config/antigravity-ide", ".config/Google/Antigravity", ".local/share/antigravity", ".local/share/Antigravity"]:
            roots.add(os.path.join(h, *sub.split("/")))
        for p in glob.glob(os.path.join(h, ".antigravity*")):
            if not any(x in os.path.basename(p) for x in ["suite-manager", ".bak", ".removed"]):
                roots.add(p)
        for p in glob.glob(os.path.join(h, ".gemini*")):
            if not any(x in os.path.basename(p) for x in [".bak", ".removed"]):
                roots.add(p)
    return roots


def scan_desktop_launchers(homes: Set[str]) -> Set[str]:
    """Inspect desktop launchers for custom data directories."""
    locs = ["/usr/share/applications", "/usr/local/share/applications"] + [os.path.join(h, ".local", "share", "applications") for h in homes]
    custom_roots: Set[str] = set()
    for d_dir in locs:
        if not os.path.isdir(d_dir):
            continue
        for d_file in glob.glob(os.path.join(d_dir, "*.desktop")):
            try:
                with open(d_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "antigravity" in content.lower() or "gemini" in content.lower():
                    for pattern in [r'--user-data-dir=(?:"([^"]+)"|\'([^\']+)\'|([^\s"\']+))',
                                    r'GEMINI_DIR=(?:"([^"]+)"|\'([^\']+)\'|([^\s"\']+))',
                                    r'--profile-directory=(?:"([^"]+)"|\'([^\']+)\'|([^\s"\']+))']:
                        for m in re.finditer(pattern, content):
                            val = m.group(1) or m.group(2) or m.group(3)
                            if val and (pattern != r'--profile-directory=(?:"([^"]+)"|\'([^\']+)\'|([^\s"\']+))' or val.startswith("/") or val.startswith("~")):
                                custom_roots.add(os.path.expanduser(val.strip()))
            except Exception:
                pass
    return custom_roots
