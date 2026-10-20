"""Conversation cascade to Google Account bindings repository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional
from antigravity_suite.multi_account.models import ConversationBinding
from antigravity_suite.multi_account.vault import get_accounts_dir


def get_bindings_file() -> Path:
    return get_accounts_dir() / "bindings.json"


def load_bindings() -> Dict[str, ConversationBinding]:
    bf = get_bindings_file()
    if not bf.is_file():
        return {}
    try:
        with open(bf, "r", encoding="utf-8") as f:
            raw = json.load(f)
        res: Dict[str, ConversationBinding] = {}
        for k, v in raw.items():
            if isinstance(v, dict):
                res[k] = ConversationBinding(
                    cascade_id=k, email=v.get("email", ""),
                    model=v.get("model", ""), updated_at=v.get("updated_at", ""),
                )
            elif isinstance(v, str):
                res[k] = ConversationBinding(cascade_id=k, email=v)
        return res
    except Exception:
        return {}


def save_bindings(bindings: Dict[str, ConversationBinding]) -> None:
    bf = get_bindings_file()
    active = get_active_account()
    data = {
        k: {"cascade_id": b.cascade_id, "email": b.email, "model": b.model, "updated_at": b.updated_at}
        for k, b in bindings.items()
    }
    if active:
        data["__active_account"] = active
    tmp = bf.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(bf)


def get_active_account() -> Optional[str]:
    bf = get_bindings_file()
    if not bf.is_file():
        return None
    try:
        with open(bf, "r", encoding="utf-8") as f:
            return json.load(f).get("__active_account")
    except Exception:
        return None


def set_active_account(email: str) -> None:
    if not email:
        return
    bf = get_bindings_file()
    raw = {}
    if bf.is_file():
        try:
            with open(bf, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            pass
    raw["__active_account"] = email
    tmp = bf.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2)
    tmp.replace(bf)


def get_account_for_cascade(cascade_id: str) -> Optional[str]:
    return load_bindings().get(cascade_id).email if (cascade_id and load_bindings().get(cascade_id)) else None


def bind_cascade_to_account(cascade_id: str, email: str, model: str = "") -> None:
    if cascade_id and email:
        bindings = load_bindings()
        bindings[cascade_id] = ConversationBinding(cascade_id=cascade_id, email=email, model=model)
        save_bindings(bindings)


def unbind_cascade(cascade_id: str) -> bool:
    bindings = load_bindings()
    if cascade_id in bindings:
        del bindings[cascade_id]
        save_bindings(bindings)
        return True
    return False
