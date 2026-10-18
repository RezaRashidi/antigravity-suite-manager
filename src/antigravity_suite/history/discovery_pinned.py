"""
Pinned Conversation Discovery and Cross-Profile Synchronization.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional, Set


def discover_pinned_conversation_ids(user_home: Optional[Path] = None) -> Set[str]:
    """Discovers all pinned conversation UUIDs across app_storage.json and annotations."""
    home = Path(user_home).resolve() if user_home else Path.home().resolve()
    pinned_ids: Set[str] = set()
    found_app_storage = False

    candidates = [
        home / ".config" / "Antigravity" / "app_storage.json",
        home / ".config" / "Antigravity IDE" / "app_storage.json",
    ] + list(home.glob(".antigravity-profile*/.config/Antigravity/app_storage.json"))

    stores = sorted([p for p in candidates if p.is_file()], key=lambda p: os.path.getmtime(p), reverse=True)
    for app_store in stores:
        try:
            with open(app_store, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "pinned_conversations_order" in data or "pinnedConversations" in data:
                found_app_storage = True
                raw = data.get("pinned_conversations_order") or data.get("pinnedConversations") or []
                raw_list = json.loads(raw) if isinstance(raw, str) else (raw if isinstance(raw, list) else [])
                for cid in raw_list:
                    if isinstance(cid, str) and len(cid) >= 32:
                        pinned_ids.add(cid.strip())
                break
        except Exception:
            pass

    if not found_app_storage:
        anno_dirs = [
            home / ".gemini" / "antigravity" / "annotations",
            home / ".gemide" / "antigravity-ide" / "annotations",
        ] + list(home.glob(".antigravity-profile*/.gemini/antigravity/annotations"))
        for ad in [d for d in anno_dirs if d.is_dir()]:
            for pbtxt in ad.glob("*.pbtxt"):
                try:
                    with open(pbtxt, "r", encoding="utf-8", errors="ignore") as f:
                        if re.search(r"pinned\s*:\s*true", f.read(), re.IGNORECASE):
                            pinned_ids.add(pbtxt.stem.strip())
                except Exception:
                    pass

    return pinned_ids


def replicate_pinned_conversations_order(pinned_ids: Set[str], user_home: Optional[Path] = None) -> None:
    """Synchronizes pinned conversations order across all app_storage.json profiles."""
    home = Path(user_home).resolve() if user_home else Path.home().resolve()
    candidates = [home / ".config" / "Antigravity" / "app_storage.json"] + list(home.glob(".antigravity-profile*/.config/Antigravity/app_storage.json"))

    for app_store in [p for p in candidates if p.is_file()]:
        try:
            with open(app_store, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw = data.get("pinned_conversations_order", [])
            was_str = isinstance(raw, str)
            existing = json.loads(raw) if was_str else (raw if isinstance(raw, list) else [])
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
