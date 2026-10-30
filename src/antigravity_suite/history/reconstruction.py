"""
Database Reconstruction Engine from Transcript Logs.

Analyzes brain folders across all pools, selects the most complete and authentic
transcript files, and synthesizes missing or damaged SQLite conversation databases.
"""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from antigravity_suite.history.synthesizer import (
    is_synthesized_db_incomplete,
    repair_database_step_gaps,
    synthesize_db_from_transcript,
)


def gather_candidate_transcripts(
    brain_pools: List[str],
    master_brain_dir: Path,
    tombstones: Optional[Set[str]] = None,
    subagents: Optional[Set[str]] = None,
) -> Dict[str, str]:
    """Scans brain pools and gathers the most complete transcript log file per UUID."""
    candidate_transcripts: Dict[str, str] = {}
    all_brain_pools = [str(master_brain_dir)] + [
        p for p in brain_pools if os.path.realpath(p) != str(master_brain_dir)
    ]

    for b_pool in all_brain_pools:
        if not os.path.isdir(b_pool):
            continue
        for b_item in glob.glob(os.path.join(b_pool, "*")):
            if not os.path.isdir(b_item):
                continue
            c_uuid = os.path.basename(b_item)
            if not re.match(r"^[0-9a-fA-F-]{36}$", c_uuid):
                continue
            if (tombstones and c_uuid in tombstones) or (subagents and c_uuid in subagents):
                continue

            tf = os.path.join(b_item, ".system_generated", "logs", "transcript_full.jsonl")
            if not os.path.isfile(tf):
                tf = os.path.join(b_item, ".system_generated", "logs", "transcript.jsonl")

            if os.path.isfile(tf):
                prev = candidate_transcripts.get(c_uuid)
                if not prev or os.path.getsize(tf) > os.path.getsize(prev):
                    candidate_transcripts[c_uuid] = tf

    return candidate_transcripts


def reconstruct_missing_databases(
    brain_pools: List[str],
    master_brain_dir: Path,
    master_conv_dir: Path,
    force_rebuild: bool = False,
    tombstones: Optional[Set[str]] = None,
    subagents: Optional[Set[str]] = None,
) -> int:
    """Reconstructs missing SQLite databases from authentic transcripts, skipping tombstones and subagents."""
    databases_reconstructed = 0
    candidate_transcripts = gather_candidate_transcripts(
        brain_pools, master_brain_dir, tombstones=tombstones, subagents=subagents
    )

    for c_uuid, tf in candidate_transcripts.items():
        if (tombstones and c_uuid in tombstones) or (subagents and c_uuid in subagents):
            continue
        target_db = master_conv_dir / f"{c_uuid}.db"
        if not target_db.exists() or is_synthesized_db_incomplete(target_db) or force_rebuild:
            if synthesize_db_from_transcript(c_uuid, target_db, tf):
                databases_reconstructed += 1
        elif target_db.exists():
            repaired = repair_database_step_gaps(target_db, tf)
            if repaired > 0:
                databases_reconstructed += 1

    return databases_reconstructed

