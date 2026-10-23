"""
Conversation Text and Title Extraction Engine.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, Tuple, Union

from antigravity_suite.history.extractor_brain import extract_brain_title, find_brain_folder
from antigravity_suite.history.extractor_checkpoint import parse_step23_checkpoint_title
from antigravity_suite.history.extractor_cleaners import get_file_stat
from antigravity_suite.history.synthesizer import parse_step14_user_prompt
from antigravity_suite.history.title_fallback import is_workspace_fallback_title

_EXTRACT_CACHE: Dict[Tuple[str, int, int, str, int, int], Tuple[str, str]] = {}


def _read_transcript_prompts(t_str: str) -> Tuple[str, str]:
    if not t_str:
        return "", ""
    t_cands = [t_str]
    if "transcript_full.jsonl" in t_str and os.path.isfile(t_str.replace("transcript_full.jsonl", "transcript.jsonl")):
        t_cands.insert(0, t_str.replace("transcript_full.jsonl", "transcript.jsonl"))
    elif not os.path.isfile(t_str) and os.path.isfile(t_str.replace("transcript.jsonl", "transcript_full.jsonl")):
        t_cands.append(t_str.replace("transcript.jsonl", "transcript_full.jsonl"))

    first, latest = "", ""
    for tf in [p for p in t_cands if os.path.isfile(p)]:
        try:
            with open(tf, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        src, typ, content = entry.get("source", ""), entry.get("type", ""), entry.get("content", "")
                        if isinstance(content, str) and (typ == "USER_INPUT" or (src == "USER_EXPLICIT" and typ not in ["VIEW_FILE", "CODE_ACTION"])):
                            m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                            clean = m.group(1).strip() if m else content.strip()
                            if clean:
                                first = first or clean
                                latest = clean
                    except Exception:
                        pass
            if first:
                break
        except Exception:
            pass
    return first, latest


def extract_conv_text(db_path: Union[str, Path], transcript_path: Union[str, Path]) -> Tuple[str, str]:
    """Extracts (title, preview) from transcript, artifacts, and sqlite steps."""
    db_stat, tr_stat = get_file_stat(db_path), get_file_stat(transcript_path)
    cache_key = (str(db_path) if db_path else "", db_stat[0], db_stat[1], str(transcript_path) if transcript_path else "", tr_stat[0], tr_stat[1])
    if cache_key in _EXTRACT_CACHE:
        return _EXTRACT_CACHE[cache_key]

    t_str, db_str = str(transcript_path) if transcript_path else "", str(db_path) if db_path else ""
    first_p, latest_p = _read_transcript_prompts(t_str)
    checkpoint_title = ""

    if os.path.isfile(db_str):
        try:
            with sqlite3.connect(db_str, timeout=15.0) as conn:
                cur = conn.cursor()
                for cp_row in cur.execute("SELECT step_payload FROM steps WHERE step_type = 23 ORDER BY idx DESC LIMIT 5;").fetchall():
                    if cp_row and cp_row[0]:
                        cand = parse_step23_checkpoint_title(cp_row[0]) or ""
                        if cand and not is_workspace_fallback_title(cand):
                            checkpoint_title = cand
                            break
                if not first_p or not latest_p:
                    f_row = cur.execute("SELECT step_payload FROM steps WHERE step_type = 14 ORDER BY idx ASC LIMIT 1;").fetchone()
                    first_p = first_p or (parse_step14_user_prompt(f_row[0]) if (f_row and f_row[0]) else "")
                    l_row = cur.execute("SELECT step_payload FROM steps WHERE step_type = 14 ORDER BY idx DESC LIMIT 1;").fetchone()
                    latest_p = latest_p or (parse_step14_user_prompt(l_row[0]) if (l_row and l_row[0]) else "")
        except Exception:
            pass

    brain_dir = find_brain_folder(t_str, db_str)
    title = checkpoint_title or extract_brain_title(brain_dir)
    res = (title, latest_p or first_p or "")
    if len(_EXTRACT_CACHE) > 5000:
        _EXTRACT_CACHE.clear()
    _EXTRACT_CACHE[cache_key] = res
    return res
