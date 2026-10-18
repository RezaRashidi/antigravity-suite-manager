"""
Title and Metadata Anomaly Detectors for History Synchronization.

Provides heuristic safety rules to detect prompt leaks, regressions,
unsanitized context mentions, and partition errors.
"""

from __future__ import annotations

import re
from typing import List, Optional


def detect_title_anomalies(
    new_title: Optional[str],
    old_title: Optional[str] = None,
    workspace_uri: Optional[str] = None,
) -> List[str]:
    """
    Evaluates a title for prompt leaks, regressions, or formatting mistakes.
    Returns a list of anomaly codes. An empty list indicates a healthy title.
    """
    anomalies: List[str] = []
    if not new_title or not new_title.strip():
        anomalies.append("EMPTY_OR_WHITESPACE_TITLE")
        return anomalies

    s = new_title.strip()

    # 1. Prompt leak checks: newlines or shell command prefixes
    if "\n" in s or "\r" in s:
        anomalies.append("PROMPT_LEAK_NEWLINE")

    shell_prefixes = (
        "curl ", "docker ", "git ", "ssh ", "sudo ",
        "cd ", "python ", "npm ", "bash ", "cat ", "ls ", "export "
    )
    if s.startswith(shell_prefixes):
        anomalies.append("PROMPT_LEAK_SHELL_COMMAND")

    # 2. Context mention leaks (@[filename])
    if "@[" in s or ("]" in s and "@" in s):
        anomalies.append("UNSANITIZED_CONTEXT_MENTION")

    # 3. Excessive length (titles should be concise topics)
    if len(s) > 75:
        anomalies.append(f"EXCESSIVE_TITLE_LENGTH_{len(s)}_CHARS")

    # 4. Question mark prompt leak for longer sentences
    if s.endswith("?") and len(s) > 35:
        anomalies.append("PROMPT_LEAK_QUESTION_SENTENCE")

    # 5. Regression detection: clean specific title downgraded to generic
    generic_names = {"Conversation", "Untitled Conversation", "IDE Conversation", "---"}
    if old_title and old_title.strip() not in generic_names and s in generic_names:
        anomalies.append(f"TITLE_REGRESSION_FROM_{old_title.strip()}")

    # 6. Missed workspace fallback
    if s in generic_names and workspace_uri and "outside-of-project" not in workspace_uri:
        anomalies.append("MISSED_WORKSPACE_TITLE_FALLBACK")

    return anomalies


def detect_partition_anomalies(
    partition: str,
    workspace_uri: Optional[str],
) -> List[str]:
    """Detects invalid partition strings. Valid standard partition is 'antigravity'."""
    anomalies: List[str] = []
    if partition not in ("antigravity", "antigravity-ide"):
        anomalies.append(f"UNKNOWN_PARTITION_{partition}")
    return anomalies
