"""
Ingestion Engine for IDE state.vscdb Conversation Summaries.
"""

from __future__ import annotations

import base64
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set

from antigravity_suite.history.extractor import (
    extract_conv_prompts,
    is_clean_title,
    is_prompt_text,
)
from antigravity_suite.history.vscdb_ingest_new import insert_new_from_ide
from antigravity_suite.history.vscdb_ingest_update import update_existing_from_ide
from antigravity_suite.proto.cascade import parse_cascade_summary
from antigravity_suite.proto.wire import extract_entries_from_proto, extract_pure_binary_summary


def ingest_vscdb_summaries(
    candidate_vscdbs: List[Path],
    all_summaries: Dict[str, bytes],
    master_conv_dir: Path,
    con: sqlite3.Connection,
    pinned_set: Optional[Set[str]] = None,
    clean_prompts: Optional[Set[str]] = None,
    tombstones: Optional[Set[str]] = None,
) -> int:
    """Reads conversation titles from VS Code state.vscdb and enriches master summaries."""
    ide_ingested_total = 0
    cur = con.cursor()

    for vscdb_p in candidate_vscdbs:
        if not vscdb_p.is_file():
            continue
        try:
            with sqlite3.connect(str(vscdb_p), timeout=15.0) as v_con:
                rows = v_con.cursor().execute(
                    "SELECT value FROM ItemTable WHERE key IN ('antigravityUnifiedStateSync.trajectorySummaries', 'antigravityUnifiedStateSync');"
                ).fetchall()
                for r in rows:
                    if not r[0]:
                        continue
                    entries = extract_entries_from_proto(base64.b64decode(r[0]))
                    for u_id, p_bin in entries.items():
                        if tombstones and u_id in tombstones:
                            continue
                        raw = extract_pure_binary_summary(p_bin)
                        if not raw:
                            continue
                        parsed = parse_cascade_summary(raw)
                        db_p = master_conv_dir / f"{u_id}.db"
                        tr_p = master_conv_dir.parent / "brain" / u_id / ".system_generated" / "logs" / "transcript.jsonl"
                        conv_prompts = clean_prompts if clean_prompts is not None else extract_conv_prompts(db_p, tr_p)
                        ide_sum, ide_annot = (parsed.get("summary") or "").strip(), (parsed.get("title") or "").strip()

                        ide_title = ""
                        for cand in [ide_sum, ide_annot]:
                            if cand and is_clean_title(cand) and not is_prompt_text(cand, conv_prompts) and cand not in ["Conversation", "Untitled Conversation"]:
                                ide_title = cand
                                break

                        if u_id in all_summaries:
                            curr_parsed = parse_cascade_summary(all_summaries[u_id])
                            curr_t = (curr_parsed.get("title") or curr_parsed.get("summary") or "").strip()
                            if curr_t and is_clean_title(curr_t) and curr_t not in ["Conversation", "Untitled Conversation"] and "@[" not in curr_t:
                                continue
                            if update_existing_from_ide(u_id, ide_title, curr_t, curr_parsed, conv_prompts, all_summaries, db_p, cur, master_conv_dir, pinned_set):
                                ide_ingested_total += 1
                        else:
                            title_to_use = ide_title or ide_sum or ide_annot or "Conversation"
                            insert_new_from_ide(u_id, title_to_use, parsed, all_summaries, db_p, con, master_conv_dir, pinned_set)
                            ide_ingested_total += 1
                con.commit()
        except Exception:
            pass

    return ide_ingested_total
