"""
High-Fidelity SQLite Conversation Database Synthesizer Facade.
"""

from __future__ import annotations

from antigravity_suite.history.synthesizer_build import (
    synthesize_db_from_transcript,
)
from antigravity_suite.history.synthesizer_inspect import (
    _VERIFIED_COMPLETE_DBS,
    clear_synthesized_db_cache,
    has_tag_in_proto,
    is_synthesized_db_incomplete,
)
from antigravity_suite.history.synthesizer_prompt import (
    parse_step14_user_prompt,
)
from antigravity_suite.history.synthesizer_repair import (
    repair_database_step_gaps,
)
from antigravity_suite.history.synthesizer_workspace import (
    extract_workspace_from_transcript,
)

_has_tag_in_proto = has_tag_in_proto

__all__ = [
    "_has_tag_in_proto",
    "has_tag_in_proto",
    "_VERIFIED_COMPLETE_DBS",
    "clear_synthesized_db_cache",
    "is_synthesized_db_incomplete",
    "parse_step14_user_prompt",
    "extract_workspace_from_transcript",
    "synthesize_db_from_transcript",
    "repair_database_step_gaps",
]
