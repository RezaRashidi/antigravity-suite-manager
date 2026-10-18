"""
VS Code Global Storage (state.vscdb) Synchronization Facade.
"""

from __future__ import annotations

from antigravity_suite.history.vscdb_discovery import (
    discover_candidate_vscdbs,
)
from antigravity_suite.history.vscdb_ingest import (
    ingest_vscdb_summaries,
)
from antigravity_suite.history.vscdb_meta import (
    get_db_trajectory_meta,
)
from antigravity_suite.history.vscdb_writer import (
    write_vscdb_unified_state,
)

__all__ = [
    "get_db_trajectory_meta",
    "discover_candidate_vscdbs",
    "ingest_vscdb_summaries",
    "write_vscdb_unified_state",
]
