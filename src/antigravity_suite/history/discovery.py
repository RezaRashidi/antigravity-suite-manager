"""
Deep Heuristic Discovery Engine for Antigravity History Stores and Multi-Instance Profiles.

Dynamically discovers conversation database stores, brain folders, desktop launchers,
and backup history repositories across the filesystem without hardcoded usernames or fixed paths.
"""

from __future__ import annotations

import getpass
import glob
import json
import os
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

from antigravity_suite.config import DEFAULT_CONFIG, get_user_home


def discover_all_history_sources(
    target_dir: Optional[Union[str, Path]] = None,
    user_home: Optional[Union[str, Path]] = None,
    source_dir: Optional[Union[str, Path]] = None,
) -> Tuple[List[str], List[str], List[str]]:
    """
    Thoroughly discovers all conversation databases, brain directories, and custom
    installation paths across the system, including manual installations, older backups,
    standalone IDE stores, desktop launchers, and multi-account user profiles.

    Returns:
      (conv_pools, brain_pools, ide_candidates)
    """
    effective_home = str(user_home) if user_home else str(get_user_home())

    # 1. Collect candidate user homes (handles running inside subprofile e.g. ~/.antigravity-profile2)
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

    conv_dirs: Set[str] = set()
    brain_dirs: Set[str] = set()
    ide_candidates: Set[str] = set()

    # 2. Add explicit target and source directories if provided
    search_roots: Set[str] = set()
    if target_dir:
        t_path = os.path.realpath(str(target_dir))
        if os.path.isdir(t_path):
            search_roots.add(t_path)
            if glob.glob(os.path.join(t_path, "*.db")):
                conv_dirs.add(t_path)
            if "conversations" in os.path.basename(t_path):
                conv_dirs.add(t_path)
            if "brain" in os.path.basename(t_path):
                brain_dirs.add(t_path)

    if source_dir:
        s_path = os.path.realpath(str(source_dir))
        if os.path.isdir(s_path):
            search_roots.add(s_path)
            if glob.glob(os.path.join(s_path, "*.db")):
                conv_dirs.add(s_path)
            if "conversations" in os.path.basename(s_path):
                conv_dirs.add(s_path)
            if "brain" in os.path.basename(s_path):
                brain_dirs.add(s_path)

    # 3. Known profile roots across all homes
    for h in homes:
        if not os.path.isdir(h):
            continue
        search_roots.add(os.path.join(h, ".gemini"))
        search_roots.add(os.path.join(h, ".gemini-ide"))
        search_roots.add(os.path.join(h, ".gemide"))
        search_roots.add(os.path.join(h, ".config", "Antigravity"))
        search_roots.add(os.path.join(h, ".config", "Antigravity IDE"))
        search_roots.add(os.path.join(h, ".config", "antigravity-ide"))
        search_roots.add(os.path.join(h, ".config", "Google", "Antigravity"))
        search_roots.add(os.path.join(h, ".local", "share", "antigravity"))
        search_roots.add(os.path.join(h, ".local", "share", "Antigravity"))
        for p in glob.glob(os.path.join(h, ".antigravity*")):
            bname = os.path.basename(p)
            if "suite-manager" not in bname and ".bak" not in bname and ".removed" not in bname:
                search_roots.add(p)
        for p in glob.glob(os.path.join(h, ".gemini*")):
            bname = os.path.basename(p)
            if ".bak" not in bname and ".removed" not in bname:
                search_roots.add(p)

    # 4. Inspect desktop launchers for custom data directories
    desktop_locations = [
        "/usr/share/applications",
        "/usr/local/share/applications",
    ]
    for h in homes:
        desktop_locations.append(os.path.join(h, ".local", "share", "applications"))

    for d_dir in desktop_locations:
        if os.path.isdir(d_dir):
            for d_file in glob.glob(os.path.join(d_dir, "*.desktop")):
                try:
                    with open(d_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if "antigravity" in content.lower() or "gemini" in content.lower():
                            for m in re.finditer(r'--user-data-dir=(?:"([^"]+)"|\'([^\']+)\'|([^\s"\']+))', content):
                                val = m.group(1) or m.group(2) or m.group(3)
                                if val:
                                    search_roots.add(os.path.expanduser(val.strip()))
                            for m in re.finditer(r'GEMINI_DIR=(?:"([^"]+)"|\'([^\']+)\'|([^\s"\']+))', content):
                                val = m.group(1) or m.group(2) or m.group(3)
                                if val:
                                    search_roots.add(os.path.expanduser(val.strip()))
                            for m in re.finditer(r'--profile-directory=(?:"([^"]+)"|\'([^\']+)\'|([^\s"\']+))', content):
                                val = m.group(1) or m.group(2) or m.group(3)
                                if val and (val.startswith("/") or val.startswith("~")):
                                    search_roots.add(os.path.expanduser(val.strip()))
                except Exception:
                    pass

    # 5. Inspect known IDE candidate subdirectories
    for root in search_roots:
        if not os.path.isdir(root) or "suite-manager" in os.path.realpath(root):
            continue
        for sub_ide in ["antigravity-ide", "antigravity"]:
            ide_p = os.path.join(root, sub_ide)
            if os.path.isdir(ide_p):
                ide_candidates.add(os.path.realpath(ide_p))

    # 6. Targeted recursive scan across discovered roots (depth <= 5)
    uuid_pattern = re.compile(r"^[0-9a-fA-F-]{36}$")
    uuid_db_pattern = re.compile(r"^[0-9a-fA-F-]{36}\.db$")

    for root_dir in sorted(search_roots):
        if not os.path.isdir(root_dir) or "suite-manager" in os.path.realpath(root_dir):
            continue
        try:
            for root, dirs, files in os.walk(root_dir, topdown=True, followlinks=False):
                # Depth limit: max 5 levels deep
                rel = os.path.relpath(root, root_dir)
                if rel != "." and len(rel.split(os.sep)) > 5:
                    dirs.clear()
                    continue
                # Prune out backup, version control, and temporary directories
                dirs[:] = [
                    d for d in dirs
                    if not any(
                        x in d.lower()
                        for x in [".bak", ".removed", "_bak", "backup", "backups", "suite-manager", ".git", "node_modules", "cache"]
                    )
                ]
                root_lower = root.lower()
                if any(x in root_lower for x in [".bak", ".removed", "_bak", "backup", "backups", "suite-manager", ".git", "node_modules"]):
                    dirs.clear()
                    continue

                # Heuristic A: Conversation database directory
                has_conv_db = any(uuid_db_pattern.match(f) for f in files)
                bname = os.path.basename(root).lower()

                if has_conv_db:
                    conv_dirs.add(os.path.realpath(root))
                elif "conversations" in bname and (has_conv_db or any(f.endswith(".db") for f in files)):
                    conv_dirs.add(os.path.realpath(root))

                # Heuristic B: Brain directory
                if "brain" in bname and (dirs or any(uuid_pattern.match(d) for d in dirs)):
                    brain_dirs.add(os.path.realpath(root))
                elif any(uuid_pattern.match(d) for d in dirs):
                    # Check if subfolders contain .system_generated
                    for d in dirs:
                        if uuid_pattern.match(d) and os.path.isdir(os.path.join(root, d, ".system_generated")):
                            brain_dirs.add(os.path.realpath(root))
                            break
        except Exception:
            pass

    def dedupe(paths: Set[str]) -> List[str]:
        seen = set()
        out = []
        for p in sorted(paths):
            rp = os.path.realpath(p)
            if rp not in seen and os.path.exists(rp):
                seen.add(rp)
                out.append(rp)
        return out

    return dedupe(conv_dirs), dedupe(brain_dirs), dedupe(ide_candidates)


def discover_pinned_conversation_ids(user_home: Optional[Path] = None) -> Set[str]:
    """
    Discovers all pinned conversation UUIDs across all app_storage.json configs
    and annotations/*.pbtxt files.
    """
    home = Path(user_home).resolve() if user_home else Path.home().resolve()
    pinned_ids: Set[str] = set()
    found_app_storage = False

    # 1. Search candidate app_storage.json locations (authoritative for Desktop UI)
    candidate_app_storages = [
        home / ".config" / "Antigravity" / "app_storage.json",
        home / ".config" / "Antigravity IDE" / "app_storage.json",
    ]
    for p in home.glob(".antigravity-profile*/.config/Antigravity/app_storage.json"):
        candidate_app_storages.append(p)

    for app_store in candidate_app_storages:
        if app_store.is_file():
            found_app_storage = True
            try:
                with open(app_store, "r", encoding="utf-8") as f:
                    data = json.load(f)
                raw_val = data.get("pinned_conversations_order", [])
                if isinstance(raw_val, str):
                    try:
                        raw_val = json.loads(raw_val)
                    except Exception:
                        raw_val = []
                if isinstance(raw_val, list):
                    for c_id in raw_val:
                        if isinstance(c_id, str) and len(c_id) >= 32:
                            pinned_ids.add(c_id.strip())
            except Exception:
                pass

    # 2. Search candidate annotations directories only as fallback if no app_storage.json exists
    if not found_app_storage:
        anno_dirs = [
            home / ".gemini" / "antigravity" / "annotations",
            home / ".gemide" / "antigravity-ide" / "annotations",
        ]
        for p in home.glob(".antigravity-profile*/.gemini/antigravity/annotations"):
            anno_dirs.append(p)

        for ad in anno_dirs:
            if ad.is_dir():
                for pbtxt in ad.glob("*.pbtxt"):
                    try:
                        with open(pbtxt, "r", encoding="utf-8", errors="ignore") as f:
                            if re.search(r"pinned\s*:\s*true", f.read(), re.IGNORECASE):
                                pinned_ids.add(pbtxt.stem.strip())
                    except Exception:
                        pass

    return pinned_ids


def replicate_pinned_conversations_order(
    pinned_ids: Set[str],
    user_home: Optional[Path] = None,
) -> None:
    """
    Ensures all discovered app_storage.json files accurately reflect the complete
    set of pinned conversation IDs, adding new pins and removing unpinned ones.
    """
    home = Path(user_home).resolve() if user_home else Path.home().resolve()
    candidate_app_storages = [
        home / ".config" / "Antigravity" / "app_storage.json",
    ]
    for p in home.glob(".antigravity-profile*/.config/Antigravity/app_storage.json"):
        candidate_app_storages.append(p)

    for app_store in candidate_app_storages:
        if app_store.is_file():
            try:
                with open(app_store, "r", encoding="utf-8") as f:
                    data = json.load(f)
                raw_val = data.get("pinned_conversations_order", [])
                was_str = isinstance(raw_val, str)
                if was_str:
                    try:
                        existing = json.loads(raw_val)
                    except Exception:
                        existing = []
                elif isinstance(raw_val, list):
                    existing = raw_val
                else:
                    existing = []

                # Preserve order of existing pinned items that remain pinned,
                # drop items that were unpinned, and append any new pinned_ids
                merged = [pid for pid in existing if pid in pinned_ids]
                for pid in sorted(pinned_ids):
                    if pid not in merged:
                        merged.append(pid)

                if merged != existing:
                    data["pinned_conversations_order"] = json.dumps(merged) if was_str else merged
                    with open(app_store, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
            except Exception:
                pass

