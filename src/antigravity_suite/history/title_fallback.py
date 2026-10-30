"""
Deterministic Workspace Fallback Title Verification.
Checks if candidate title matches constructible fallback titles for given workspace(s).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Set

GENERIC_FALLBACK_TITLES = {
    "conversation",
    "untitled conversation",
    "new chat",
    "chat",
    "",
}

_NL_STOPWORDS = {"how", "to", "a", "the", "fork", "why", "what", "where", "can", "with"}


def get_constructible_fallback_titles(
    workspace: Optional[str] = None,
    candidate_workspaces: Optional[Iterable[str]] = None,
) -> Set[str]:
    """Generates the exact set of fallback titles that can be constructed for given workspace(s)."""
    fallbacks = {t.lower() for t in GENERIC_FALLBACK_TITLES}
    ws_list = []
    if workspace:
        ws_list.append(str(workspace).strip())
    if candidate_workspaces:
        for cw in candidate_workspaces:
            if cw:
                ws_list.append(str(cw).strip())

    for ws in ws_list:
        raw_name = Path(ws).name.strip()
        clean_name = raw_name.replace("-", " ").replace("_", " ").strip().title()
        for variant in [raw_name, clean_name]:
            if variant:
                fallbacks.add(f"{variant.lower()} chat")
    return fallbacks


def is_workspace_fallback_title(
    title: Optional[str],
    fallback_workspace: Optional[str] = None,
    candidate_workspaces: Optional[Iterable[str]] = None,
) -> bool:
    """Returns True if title matches a constructible workspace fallback title or generic placeholder."""
    if not title or not isinstance(title, str):
        return True
    s = title.strip()
    if not s or s.lower().startswith("desktop:"):
        return True
    lower_s = s.lower()
    if lower_s in GENERIC_FALLBACK_TITLES:
        return True

    # When workspace is known for this chat, check constructible titles for this chat
    if fallback_workspace or candidate_workspaces:
        constructible = get_constructible_fallback_titles(fallback_workspace, candidate_workspaces)
        return lower_s in constructible

    # Fallback when workspace is unknown: reject "<Project> Chat" directory patterns
    if lower_s.endswith(" chat") and len(lower_s) > 5:
        prefix_words = s[:-5].strip().split()
        if len(prefix_words) >= 4 or any(w.lower() in _NL_STOPWORDS for w in prefix_words):
            return False
        return True

    return False
