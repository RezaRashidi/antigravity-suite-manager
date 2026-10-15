"""
Discovery Engine for Antigravity History Stores and Multi-Instance Profiles.

Dynamically discovers conversation database stores, brain folders, and IDE profiles
across the filesystem without hardcoded usernames or fixed paths.
"""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple, Union

from antigravity.config import DEFAULT_CONFIG, get_user_home


def discover_all_history_sources(
    target_dir: Optional[Union[str, Path]] = None,
    user_home: Optional[Union[str, Path]] = None,
) -> Tuple[List[str], List[str], List[str]]:
    """
    Discovers all candidate conversation database directories, brain artifact stores,
    and IDE instance directories across the system.
    Returns:
      (conv_pools, brain_pools, ide_candidates)
    """
    effective_home = str(user_home) if user_home else str(get_user_home())
    candidate_geminis = []

    # 1. Primary standard gemini paths
    candidate_geminis.append(os.path.join(effective_home, ".gemini"))
    candidate_geminis.append(os.path.join(effective_home, ".gemide"))
    candidate_geminis.append(os.path.join(effective_home, ".gemini-ide"))

    # 2. Multi-account profile directories (e.g., ~/.antigravity-profile2/.gemini)
    for p in glob.glob(os.path.join(effective_home, ".antigravity-profile*")):
        # Avoid suite-manager itself
        if "suite-manager" in os.path.basename(p):
            continue
        g_sub = os.path.join(p, ".gemini")
        if os.path.isdir(g_sub):
            candidate_geminis.append(g_sub)
        candidate_geminis.append(p)

    # 3. Explicit target directory if provided
    if target_dir:
        candidate_geminis.append(str(target_dir))

    conv_pools = []
    brain_pools = []
    ide_candidates = []

    for g_dir in candidate_geminis:
        if not os.path.isdir(g_dir):
            continue
        # Avoid suite-manager repository folder
        if "suite-manager" in os.path.realpath(g_dir):
            continue

        # Check subclients: antigravity, antigravity-ide, antigravity-cli, antigravity-acp
        for sub in ["antigravity", "antigravity-ide", "antigravity-cli", "antigravity-acp"]:
            c_path = os.path.join(g_dir, sub, "conversations")
            b_path = os.path.join(g_dir, sub, "brain")

            if os.path.isdir(c_path):
                # Verify it has .db or .pb files
                has_files = False
                try:
                    for f in os.listdir(c_path):
                        if f.endswith(".db") or f.endswith(".pb"):
                            has_files = True
                            break
                except Exception:
                    pass
                if has_files:
                    conv_pools.append(c_path)

            if os.path.isdir(b_path):
                has_brains = False
                try:
                    for item in os.listdir(b_path):
                        if re.match(r"^[0-9a-fA-F-]{36}$", item) and os.path.isdir(os.path.join(b_path, item)):
                            has_brains = True
                            break
                except Exception:
                    pass
                if has_brains:
                    brain_pools.append(b_path)

        # Check IDE candidates
        for sub_ide in ["antigravity-ide", "antigravity"]:
            ide_p = os.path.join(g_dir, sub_ide)
            if os.path.isdir(ide_p):
                ide_candidates.append(ide_p)

    # Deduplicate while preserving order (using realpath)
    def dedupe(paths: List[str]) -> List[str]:
        seen = set()
        out = []
        for p in paths:
            rp = os.path.realpath(p)
            if rp not in seen and os.path.exists(rp):
                seen.add(rp)
                out.append(rp)
        return out

    return dedupe(conv_pools), dedupe(brain_pools), dedupe(ide_candidates)
