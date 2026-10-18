"""
Dynamic Discovery of state.vscdb Files Across Profiles.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import List, Optional


def discover_candidate_vscdbs(
    user_home: Path,
    ide_candidates: Optional[List[str]] = None,
) -> List[Path]:
    """Dynamically discovers all state.vscdb paths across profiles and standard locations."""
    candidate_vscdbs_set = set()
    homes = [user_home] if user_home else [Path(os.path.expanduser("~"))]

    for h in homes:
        h_str = str(h)
        for pattern in [
            os.path.join(h_str, ".config", "*", "User", "globalStorage", "state.vscdb"),
            os.path.join(h_str, ".config", "Google", "*", "User", "globalStorage", "state.vscdb"),
            os.path.join(h_str, ".antigravity*", ".config", "*", "User", "globalStorage", "state.vscdb"),
            os.path.join(h_str, ".config", "*", "User", "workspaceStorage", "*", "state.vscdb"),
            os.path.join(h_str, ".config", "Google", "*", "User", "workspaceStorage", "*", "state.vscdb"),
            os.path.join(h_str, ".antigravity*", ".config", "*", "User", "workspaceStorage", "*", "state.vscdb"),
        ]:
            for vpath in glob.glob(pattern):
                if any(k in vpath.lower() for k in ["antigravity", "gemini"]):
                    candidate_vscdbs_set.add(Path(vpath).resolve())

    if ide_candidates:
        for cand in ide_candidates:
            cand_p = Path(cand)
            cand_vsc = cand_p / "User" / "globalStorage" / "state.vscdb"
            if cand_vsc.is_file():
                candidate_vscdbs_set.add(cand_vsc.resolve())
            for ws_vsc in glob.glob(str(cand_p / "User" / "workspaceStorage" / "*" / "state.vscdb")):
                candidate_vscdbs_set.add(Path(ws_vsc).resolve())

    return sorted(list(candidate_vscdbs_set))
