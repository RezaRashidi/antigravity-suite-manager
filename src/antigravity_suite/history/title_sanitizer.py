"""
Title Sanitization and Normalization Engine.

Provides generic string normalization, context tag stripping,
and fallback handling for conversation titles without hardcoded phrases.
"""

from __future__ import annotations

import re
from typing import Optional, Set

from antigravity_suite.history.extractor import is_clean_title, is_prompt_text
from antigravity_suite.history.title_fallback import is_workspace_fallback_title

__all__ = [
    "is_clean_title",
    "is_prompt_text",
    "is_raw_prompt_sentence",
    "is_workspace_fallback_title",
    "sanitize_topic_title",
]


def is_raw_prompt_sentence(text: Optional[str], known_prompts: Optional[Set[str]] = None) -> bool:
    """Returns True if the text matches a known user prompt or raw terminal command."""
    if not text or not isinstance(text, str):
        return False
    s = text.strip()
    if not s:
        return False
    if known_prompts and s in known_prompts:
        return True
    if "\n" in s or "\r" in s:
        return True
    if s.startswith(("curl ", "docker ", "git ", "ssh ", "sudo ", "cd ", "npm ", "cat ", "ls ", "export ", "python ")):
        return True
    return False


def sanitize_topic_title(title: Optional[str], fallback_workspace: Optional[str] = None) -> str:
    """Generic string cleanup: strips @[file] context mentions, normalizes whitespace."""
    if not title:
        if fallback_workspace:
            clean_name = fallback_workspace.rstrip("/").split("/")[-1]
            if clean_name and clean_name != "outside-of-project":
                return f"{clean_name.replace('-', ' ').replace('_', ' ').title()} Chat"
        return "Conversation"

    s = title.strip()
    s = re.sub(r"(?:in\s*)?@\[[^\]]+\]", "", s).strip()
    s = re.sub(r"\s+", " ", s).strip()

    if not s or s in ["Conversation", "Untitled Conversation", "IDE Conversation", "---"]:
        if fallback_workspace:
            clean_name = fallback_workspace.rstrip("/").split("/")[-1]
            if clean_name and clean_name != "outside-of-project":
                return f"{clean_name.replace('-', ' ').replace('_', ' ').title()} Chat"
        return "Conversation"

    return s
