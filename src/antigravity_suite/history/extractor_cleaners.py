"""
Conversation Title and Prompt Validation and Cleaning Helpers.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Optional, Set, Tuple, Union

_PROMPT_CACHE: Dict[Tuple[str, int, int, str, int, int], Set[str]] = {}


def get_file_stat(p: Union[str, Path, None]) -> Tuple[int, int]:
    """Returns (mtime_ns, size) or (0, 0) if file does not exist."""
    if not p:
        return (0, 0)
    try:
        st = os.stat(str(p))
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return (0, 0)


def is_clean_title(val: Optional[str]) -> bool:
    """Returns True if the string is an authentic, human-readable conversation title."""
    if not val or not isinstance(val, str):
        return False
    s = val.strip()
    if not s or s in ["Conversation", "IDE Conversation", "Untitled Conversation", "---"] or len(s) < 2:
        return False
    if s.startswith(("@[", "{", "}", "[", "]", "<USER_REQUEST>", "<ADDITIONAL_METADATA>", "```", "<?php", "#!", "/*")):
        return False
    if not any(c.isalnum() for c in s):
        return False
    if re.match(r"^(?:[╰╭│├└─\s]*[❯>$#%]\s*|root@[^:]+:[^\s#$]+[#$]\s*|[a-zA-Z0-9_-]+@[^:]+:[^\s#$]+[#$]\s*)", s):
        return False
    if s.startswith(("curl ", "docker ", "git ", "ssh ", "sudo ", "cd ", "npm ", "cat ", "ls ", "export ", "bash ", "python ", "systemctl ", "journalctl ", "grep ", "http://", "https://", "import ", "def ", "class ", "return ")):
        return False
    return True


def is_prompt_text(cand: Optional[str], prompt_cands: Optional[Set[str]]) -> bool:
    """Returns True if candidate string matches any prompt variant or prefix."""
    if not cand or not isinstance(cand, str) or not prompt_cands:
        return False
    cand_s = cand.strip()
    if not cand_s:
        return False
    if cand_s in prompt_cands:
        return True
    cand_norm = re.sub(r"\s+", " ", cand_s).lower()
    for p in prompt_cands:
        p_norm = re.sub(r"\s+", " ", p).lower()
        if cand_norm == p_norm:
            return True
        min_len = min(len(cand_norm), len(p_norm))
        if min_len >= 25 and cand_norm[:min_len] == p_norm[:min_len]:
            return True
    return False
