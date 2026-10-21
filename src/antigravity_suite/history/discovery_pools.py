"""
Deep Directory Scanning for Conversation and Brain History Pools.
"""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

from antigravity_suite.history.discovery_roots import (
    get_candidate_homes,
    get_profile_search_roots,
    scan_desktop_launchers,
)


def _dedupe_existing(paths: Set[str]) -> List[str]:
    seen, out = set(), []
    for p in sorted(paths):
        rp = os.path.realpath(p)
        if rp not in seen and os.path.exists(rp):
            seen.add(rp)
            out.append(rp)
    return out


def discover_all_history_sources(
    target_dir: Optional[Union[str, Path]] = None,
    user_home: Optional[Union[str, Path]] = None,
    source_dir: Optional[Union[str, Path]] = None,
) -> Tuple[List[str], List[str], List[str]]:
    """Discovers all conversation databases, brain directories, and IDE stores."""
    homes = get_candidate_homes(user_home)
    search_roots = get_profile_search_roots(homes) | scan_desktop_launchers(homes, isolated=bool(user_home))
    conv_dirs: Set[str] = set()
    brain_dirs: Set[str] = set()
    ide_candidates: Set[str] = set()

    for d in [target_dir, source_dir]:
        if d and os.path.isdir(str(d)):
            rp = os.path.realpath(str(d))
            search_roots.add(rp)
            if glob.glob(os.path.join(rp, "*.db")) or "conversations" in os.path.basename(rp):
                conv_dirs.add(rp)
            if "brain" in os.path.basename(rp):
                brain_dirs.add(rp)

    for root in search_roots:
        if os.path.isdir(root) and "suite-manager" not in os.path.realpath(root):
            for sub in ["antigravity-ide", "antigravity"]:
                ip = os.path.join(root, sub)
                if os.path.isdir(ip):
                    ide_candidates.add(os.path.realpath(ip))

    uuid_pat = re.compile(r"^[0-9a-fA-F-]{36}$")
    uuid_db_pat = re.compile(r"^[0-9a-fA-F-]{36}\.db$")

    for root_dir in sorted(search_roots):
        if not os.path.isdir(root_dir) or "suite-manager" in os.path.realpath(root_dir):
            continue
        try:
            for root, dirs, files in os.walk(root_dir, topdown=True, followlinks=False):
                rel = os.path.relpath(root, root_dir)
                if rel != "." and len(rel.split(os.sep)) > 5:
                    dirs.clear()
                    continue
                dirs[:] = [d for d in dirs if not any(x in d.lower() for x in [".bak", ".removed", "backup", "suite-manager", ".git", "node_modules", "cache"])]
                if any(x in root.lower() for x in [".bak", ".removed", "backup", "suite-manager", ".git", "node_modules"]):
                    dirs.clear()
                    continue
                has_conv_db = any(uuid_db_pat.match(f) for f in files)
                bname = os.path.basename(root).lower()
                if has_conv_db or ("conversations" in bname and (has_conv_db or any(f.endswith(".db") for f in files))):
                    conv_dirs.add(os.path.realpath(root))
                if ("brain" in bname and dirs) or any(uuid_pat.match(d) and os.path.isdir(os.path.join(root, d, ".system_generated")) for d in dirs):
                    brain_dirs.add(os.path.realpath(root))
        except Exception:
            pass

    return _dedupe_existing(conv_dirs), _dedupe_existing(brain_dirs), _dedupe_existing(ide_candidates)
