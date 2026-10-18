"""
User Prompt Extraction and Normalization.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Set, Union

from antigravity_suite.history.extractor_cleaners import _PROMPT_CACHE, get_file_stat
from antigravity_suite.history.synthesizer import parse_step14_user_prompt


def extract_conv_prompts(
    db_path: Union[str, Path, None],
    transcript_path: Union[str, Path, None],
) -> Set[str]:
    """Extracts all user prompt text variants across DB steps and transcript logs."""
    stat_db = get_file_stat(db_path)
    stat_tr = get_file_stat(transcript_path)
    cache_key = (str(db_path) if db_path else "", stat_db[0], stat_db[1], str(transcript_path) if transcript_path else "", stat_tr[0], stat_tr[1])
    if cache_key in _PROMPT_CACHE:
        return set(_PROMPT_CACHE[cache_key])

    prompts: Set[str] = set()
    t_str = str(transcript_path) if transcript_path else ""
    if t_str and os.path.isfile(t_str):
        try:
            with open(t_str, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "USER_INPUT" or entry.get("source") == "USER_EXPLICIT":
                            content = entry.get("content", "")
                            if isinstance(content, str) and content.strip():
                                m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                                raw = m.group(1).strip() if m else content.strip()
                                if raw:
                                    prompts.add(raw)
                    except Exception:
                        pass
        except Exception:
            pass

    db_str = str(db_path) if db_path else ""
    if db_str and os.path.isfile(db_str):
        try:
            with sqlite3.connect(db_str, timeout=10.0) as conn:
                cur = conn.cursor()
                cur.execute("SELECT step_payload FROM steps WHERE step_type = 14;")
                for r in cur.fetchall():
                    if r[0]:
                        p = parse_step14_user_prompt(r[0])
                        if p and p.strip():
                            prompts.add(p.strip())
        except Exception:
            pass

    signatures: Set[str] = set()
    for p in prompts:
        signatures.add(p)
        clean = re.sub(r"(?:in\s*)?@\[[^\]]+\]", "", p).strip()
        if clean:
            signatures.add(clean)
            space_clean = re.sub(r"\s+", " ", clean).strip()
            signatures.add(space_clean)
            for l in clean.split("\n"):
                l_strip = l.strip()
                if l_strip:
                    signatures.add(l_strip)
                    sh_clean = re.sub(r"^(?:[╰╭│├└─\s]*[❯>$#%]\s*|root@[^:]+:[^\s#$]+[#$]\s*|[a-zA-Z0-9_-]+@[^:]+:[^\s#$]+[#$]\s*)", "", l_strip).strip()
                    if sh_clean:
                        signatures.add(sh_clean)
            for length in [60, 77, 80, 100]:
                if len(space_clean) >= length:
                    signatures.add(space_clean[:length].strip())

    _PROMPT_CACHE[cache_key] = signatures
    return signatures
