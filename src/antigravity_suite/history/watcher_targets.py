"""
Directory and File Discovery for Watcher Daemon.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from antigravity_suite.history.discovery import discover_all_history_sources
from antigravity_suite.history.vscdb_sync import discover_candidate_vscdbs


def get_mtime_snapshot(conv_dirs: List[str], brain_dirs: List[str], extra_files: Optional[List[str]] = None) -> Dict[str, float]:
    """Takes a dictionary snapshot of file modification times."""
    snapshot: Dict[str, float] = {}
    for d in conv_dirs:
        if os.path.isdir(d):
            for f in glob.glob(os.path.join(d, "*.db")):
                if not os.path.basename(f).startswith("conversation_summaries"):
                    try:
                        snapshot[f] = os.path.getmtime(f)
                    except Exception:
                        pass
    for b in brain_dirs:
        if os.path.isdir(b):
            for pat in [os.path.join(b, "*", ".system_generated", "logs", "*.jsonl"), os.path.join(b, "*", "*.md")]:
                for f in glob.glob(pat):
                    try:
                        snapshot[f] = os.path.getmtime(f)
                    except Exception:
                        pass
    for ef in (extra_files or []):
        if os.path.isfile(ef):
            try:
                snapshot[ef] = os.path.getmtime(ef)
            except Exception:
                pass
    return snapshot


def discover_watch_targets(effective_master: Path, home: Path) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Discovers conversation, brain, extra configuration directories, and critical state files."""
    conv_pools, brain_pools, ide_candidates = discover_all_history_sources(user_home=home)
    candidate_vscdbs = discover_candidate_vscdbs(home, ide_candidates)

    extra_dirs = list(set(
        [str(Path(p).parent) for p in candidate_vscdbs if os.path.isdir(Path(p).parent)]
        + [str(home / ".config" / "Antigravity"), str(home / ".config" / "Antigravity IDE")]
        + [str(p / ".config" / "Antigravity") for p in home.glob(".antigravity-profile*") if os.path.isdir(p / ".config" / "Antigravity")]
        + [str(p / ".config" / "Antigravity IDE") for p in home.glob(".antigravity-profile*") if os.path.isdir(p / ".config" / "Antigravity IDE")]
    ))
    extra_files = [str(p) for p in candidate_vscdbs]

    watch_conv_dirs = list(set([str(effective_master / "conversations")] + conv_pools))
    watch_brain_dirs = list(set([str(effective_master / "brain")] + brain_pools))
    return watch_conv_dirs, watch_brain_dirs, extra_dirs, extra_files
