"""
Desktop App electron storage (app_storage.json) deletion operations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from antigravity_suite.config import get_user_home


def purge_conversation_from_app_storage(conv_id: str, user_home: Optional[Path] = None) -> None:
    """Removes conversation layout references from Desktop App electron storage (app_storage.json)."""
    home = user_home or get_user_home()
    candidates = [
        home / ".config" / "Antigravity" / "app_storage.json",
        home / ".config" / "Antigravity IDE" / "app_storage.json",
    ]
    for p in home.glob(".antigravity-profile*/.config/Antigravity/app_storage.json"):
        if p not in candidates:
            candidates.append(p)
    for cand in candidates:
        if not cand.is_file():
            continue
        try:
            data = json.loads(cand.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            modified = False

            for p_key in ["pinned_conversations_order", "pinnedConversations", "pinned_conversations"]:
                if p_key in data:
                    val = data[p_key]
                    is_str = isinstance(val, str)
                    try:
                        lst = json.loads(val) if is_str else val
                    except Exception:
                        lst = []
                    if isinstance(lst, list) and conv_id in lst:
                        lst = [x for x in lst if x != conv_id]
                        data[p_key] = json.dumps(lst) if is_str else lst
                        modified = True

            if "conversationTitles" in data and isinstance(data["conversationTitles"], dict):
                if conv_id in data["conversationTitles"]:
                    data["conversationTitles"].pop(conv_id, None)
                    modified = True

            for a_key in ["aux-pane-session", "aux-pane-v2-session"]:
                if a_key in data:
                    val = data[a_key]
                    is_str = isinstance(val, str)
                    try:
                        sess = json.loads(val) if is_str else val
                    except Exception:
                        sess = {}
                    if isinstance(sess, dict) and "conversationPanes" in sess and isinstance(sess["conversationPanes"], dict):
                        if conv_id in sess["conversationPanes"]:
                            sess["conversationPanes"].pop(conv_id, None)
                            data[a_key] = json.dumps(sess) if is_str else sess
                            modified = True

            for k in list(data.keys()):
                if k.startswith("antigravity-multi-conversation-layout-v3-") and conv_id in k:
                    data.pop(k, None)
                    modified = True

            if modified:
                cand.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
