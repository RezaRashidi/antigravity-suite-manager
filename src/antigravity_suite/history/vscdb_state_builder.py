"""
Building and Merging Unified State Payloads for IDE state.vscdb.
"""

from __future__ import annotations

import base64
from typing import Dict, Optional, Tuple

from antigravity_suite.history.projects import is_valid_workspace_uri
from antigravity_suite.proto.cascade import build_cascade_summary, parse_cascade_summary
from antigravity_suite.proto.vscdb import build_summaries_state, build_unified_state_sync
from antigravity_suite.proto.wire import extract_entries_from_proto, extract_pure_binary_summary


def merge_ide_active_state(
    all_summaries: Dict[str, bytes],
    old_traj_b64: Optional[str],
    tombstones: Optional[Set[str]] = None,
    subagents: Optional[Set[str]] = None,
) -> Dict[str, bytes]:
    """Merges in-memory summaries with old IDE trajectory summaries preserving active step counts."""
    state_summaries = dict(all_summaries)
    if not old_traj_b64:
        return state_summaries
    try:
        existing_entries = extract_entries_from_proto(base64.b64decode(old_traj_b64))
        for e_cid, e_bin in existing_entries.items():
            if (tombstones and e_cid in tombstones) or (subagents and e_cid in subagents):
                continue
            e_raw = extract_pure_binary_summary(e_bin)
            if not e_raw:
                continue
            e_parsed = parse_cascade_summary(e_raw)
            if e_parsed.get("parent_conversation_id") or e_parsed.get("nesting_depth", 0) > 0:
                continue
            e_sc = e_parsed.get("step_count", 0)
            if e_cid in state_summaries:
                curr = parse_cascade_summary(state_summaries[e_cid])
                if e_sc > curr.get("step_count", 0):
                    valid_ws = curr.get("workspace_uri") if is_valid_workspace_uri(curr.get("workspace_uri")) else None
                    if not valid_ws and is_valid_workspace_uri(e_parsed.get("workspace_uri")):
                        valid_ws = e_parsed.get("workspace_uri")
                    valid_pid = curr.get("project_id") or e_parsed.get("project_id")
                    state_summaries[e_cid] = build_cascade_summary(
                        e_cid, curr.get("title") or e_parsed.get("title", ""),
                        curr.get("summary") or e_parsed.get("summary", ""), e_sc,
                        last_modified_iso=e_parsed.get("last_modified_iso") or curr.get("last_modified_iso"),
                        last_user_step=e_parsed.get("last_user_step") or curr.get("last_user_step", -1),
                        workspace_uri=valid_ws, project_id=valid_pid,
                        created_iso=curr.get("created_iso") or e_parsed.get("created_iso"),
                        last_user_input_iso=e_parsed.get("last_user_input_iso") or curr.get("last_user_input_iso"),
                        pinned=curr.get("pinned", False), archived=curr.get("archived", False),
                    )
            else:
                ws_uri = e_parsed.get("workspace_uri") if is_valid_workspace_uri(e_parsed.get("workspace_uri")) else None
                state_summaries[e_cid] = build_cascade_summary(
                    e_cid, e_parsed.get("title", ""), e_parsed.get("summary", ""), e_sc,
                    last_modified_iso=e_parsed.get("last_modified_iso"),
                    last_user_step=e_parsed.get("last_user_step", -1), workspace_uri=ws_uri,
                    project_id=e_parsed.get("project_id"), created_iso=e_parsed.get("created_iso"),
                    last_user_input_iso=e_parsed.get("last_user_input_iso"),
                    pinned=e_parsed.get("pinned", False), archived=e_parsed.get("archived", False),
                )
    except Exception:
        pass
    return state_summaries


def build_unified_payloads(state_summaries: Dict[str, bytes], old_sync_b64: Optional[str]) -> Tuple[str, str]:
    """Builds base64 encoded trajectorySummaries and antigravityUnifiedStateSync values."""
    val_wrap_b64 = build_summaries_state(state_summaries)
    outer_b64 = build_unified_state_sync(state_summaries, existing_raw_b64=old_sync_b64)
    return val_wrap_b64, outer_b64
