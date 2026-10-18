"""
Title Selection and Priority Resolution Engine.

Resolves authentic conversation titles according to strict priority order:
Existing clean title > Authentic LLM summary > Clean artifact title > Workspace fallback.
"""

from __future__ import annotations

from typing import Iterable, Optional, Set, Tuple

from antigravity_suite.history.title_sanitizer import (
    is_clean_title,
    is_prompt_text,
    is_raw_prompt_sentence,
    sanitize_topic_title,
)


def pick_first_valid_title(candidates: Iterable[Optional[str]], prompt_cands: Set[str]) -> Optional[str]:
    """Iterates through candidates and returns the first clean, non-prompt title."""
    generic_names = {"Conversation", "Untitled Conversation", "IDE Conversation", "---"}
    for cand in candidates:
        if not cand or not isinstance(cand, str):
            continue
        s = cand.strip()
        if (
            s
            and is_clean_title(s)
            and not is_prompt_text(s, prompt_cands)
            and not is_raw_prompt_sentence(s, prompt_cands)
            and s not in generic_names
        ):
            return s
    return None


def resolve_best_title(
    existing_candidates: Iterable[Optional[str]],
    llm_candidates: Iterable[Optional[str]],
    clean_artifact_title: Optional[str],
    prompt_cands: Set[str],
    fallback_workspace: Optional[str] = None,
) -> Tuple[str, str]:
    """Selects authentic title and reports the winning source."""
    existing_clean = pick_first_valid_title(existing_candidates, prompt_cands)
    if existing_clean:
        return existing_clean, "existing_clean"

    llm_clean = pick_first_valid_title(llm_candidates, prompt_cands)
    if llm_clean:
        return llm_clean, "llm_summary"

    if (
        clean_artifact_title
        and is_clean_title(clean_artifact_title)
        and not is_prompt_text(clean_artifact_title, prompt_cands)
        and not is_raw_prompt_sentence(clean_artifact_title, prompt_cands)
    ):
        return clean_artifact_title.strip(), "brain_artifact"

    fallback = sanitize_topic_title(None, fallback_workspace=fallback_workspace)
    source = "workspace_name" if fallback != "Conversation" else "default_fallback"
    return fallback, source
