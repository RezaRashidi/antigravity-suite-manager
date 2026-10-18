"""
Brain Folder Resolution and Artifact Markdown Title Extraction.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

GENERIC_BLACKLIST = {
    "task", "tasks", "implementation plan", "overview", "walkthrough",
    "architecture", "notes", "summary", "checklist", "test results",
    "verification", "instructions", "scratchpad", "conversation", "untitled conversation",
}


def find_brain_folder(t_str: str, db_str: str) -> str:
    """Resolves canonical brain directory given transcript or SQLite database paths."""
    brain_folder = ""
    if t_str:
        cand_bf = os.path.dirname(os.path.dirname(os.path.dirname(t_str)))
        conv_uuid = os.path.basename(cand_bf)
        parent_dir = os.path.dirname(cand_bf)
        if os.path.isdir(cand_bf) and any(glob.glob(os.path.join(cand_bf, "*.md"))):
            brain_folder = cand_bf
        else:
            for b_cand in [
                os.path.join(parent_dir, "brain", conv_uuid),
                os.path.join(parent_dir, "antigravity", "brain", conv_uuid),
                os.path.join(os.path.dirname(parent_dir), "brain", conv_uuid),
                os.path.join(os.path.dirname(parent_dir), "antigravity", "brain", conv_uuid),
            ]:
                if os.path.isdir(b_cand) and any(glob.glob(os.path.join(b_cand, "*.md"))):
                    brain_folder = b_cand
                    break
        if not brain_folder and os.path.isdir(cand_bf):
            brain_folder = cand_bf
    if not brain_folder and db_str:
        p_db = Path(db_str)
        cand1 = str(p_db.parent.parent / "brain" / p_db.stem)
        cand2 = str(p_db.parent.parent.parent / "brain" / p_db.stem)
        if os.path.isdir(cand1):
            brain_folder = cand1
        elif os.path.isdir(cand2):
            brain_folder = cand2
    return brain_folder


def extract_brain_title(brain_folder: str) -> str:
    """Extracts authentic H1 title from task.md, implementation_plan.md, or any .md artifact."""
    if not brain_folder or not os.path.isdir(brain_folder):
        return ""
    for art_name in ["task.md", "implementation_plan.md", "architecture.md"]:
        art_file = os.path.join(brain_folder, art_name)
        if os.path.isfile(art_file):
            try:
                with open(art_file, "r", encoding="utf-8", errors="ignore") as af:
                    for l in af:
                        l_clean = l.strip()
                        if l_clean.startswith("# ") and len(l_clean) > 3:
                            art_title = l_clean[2:].strip()
                            if art_title and art_title.lower() not in GENERIC_BLACKLIST:
                                return art_title
            except Exception:
                pass
    for af_path in glob.glob(os.path.join(brain_folder, "*.md")):
        try:
            with open(af_path, "r", encoding="utf-8", errors="ignore") as af:
                for l in af:
                    l_clean = l.strip()
                    if l_clean.startswith("# ") and len(l_clean) > 3:
                        art_title = l_clean[2:].strip()
                        if art_title and art_title.lower() not in GENERIC_BLACKLIST:
                            return art_title
        except Exception:
            pass
    return ""
