"""
Transcript Step Classification and Tool Types.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Set, Tuple

TOOL_TYPES: Set[str] = {
    "VIEW_FILE", "RUN_COMMAND", "GENERIC", "GREP_SEARCH", "LIST_DIRECTORY",
    "SEARCH_WEB", "READ_URL_CONTENT", "GENERATE_IMAGE", "ASK_QUESTION",
    "CODE_ACTION", "ERROR_MESSAGE", "WRITE_TO_FILE", "REPLACE_FILE_CONTENT",
    "MULTI_REPLACE_FILE_CONTENT", "EDIT_FILE", "FIND_BY_NAME", "BROWSER_SUBAGENT",
    "BROWSER_ACTION", "SCHEDULE", "INVOKE_SUBAGENT", "MANAGE_SUBAGENTS",
    "MANAGE_TASK", "SEND_MESSAGE",
}


def classify_transcript_step(entry: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    """Classifies a transcript line into (step_type, status) or returns None if skipped."""
    src = str(entry.get("source", "")).upper()
    typ = str(entry.get("type", "")).upper()
    st_str = str(entry.get("status", "DONE")).upper()
    content = entry.get("content", "")
    thinking = entry.get("thinking", "")
    tool_calls = entry.get("tool_calls", [])

    if typ == "CHECKPOINT":
        return 23, 3

    if typ in ["CONVERSATION_HISTORY", "KNOWLEDGE_ARTIFACTS", "EPHEMERAL_MESSAGE", "SYSTEM_MESSAGE"] or src == "SYSTEM":
        return None

    is_tool = (
        typ in TOOL_TYPES
        or bool(entry.get("tool_action") or entry.get("tool_summary"))
        or src in ["TOOL", "SYSTEM_TOOL"]
    )

    if is_tool:
        step_type = 132
    elif typ == "USER_INPUT" or (src == "USER_EXPLICIT" and not is_tool) or (
        src not in ["MODEL", "TOOL", "ASSISTANT"] and isinstance(content, str) and "<USER_REQUEST>" in content
    ):
        step_type = 14
    elif typ == "PLANNER_RESPONSE" or src == "MODEL" or thinking or tool_calls:
        step_type = 15
    else:
        if content:
            step_type = 15 if src == "MODEL" else 14
        else:
            return None

    status = 4 if st_str == "ERROR" else 3
    return step_type, status
