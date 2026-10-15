"""
Conversation Title, Preview, and Annotation Extractor.

Extracts authentic conversation titles and summaries from markdown artifacts,
transcript JSON logs, SQLite step tables, and .pbtxt annotation files.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, Union

from antigravity.history.synthesizer import parse_step14_user_prompt


def get_annotation_title(gemini_dir: Union[str, Path], conv_id: str) -> Optional[str]:
    """Reads authentic title from annotations/<conv_id>.pbtxt if present."""
    anno_file = os.path.join(str(gemini_dir), "annotations", f"{conv_id}.pbtxt")
    if os.path.isfile(anno_file):
        try:
            with open(anno_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            m = re.search(r'title\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', content)
            if m:
                clean_title = m.group(1).encode("utf-8").decode("unicode_escape").strip()
                if clean_title and clean_title not in ["Conversation", "Untitled Conversation"]:
                    return clean_title
        except Exception:
            pass
    return None


def sync_annotation_file(master_gemini: Union[str, Path], conv_id: str, title: str) -> bool:
    """Ensures annotations/<conv_id>.pbtxt exists and has title so Desktop App shows it."""
    if not title or title.strip() in ["", "Conversation", "Untitled Conversation"]:
        return False

    anno_dir = os.path.join(str(master_gemini), "annotations")
    os.makedirs(anno_dir, exist_ok=True)
    anno_file = os.path.join(anno_dir, f"{conv_id}.pbtxt")

    clean_title = title.strip().replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    title_line = f'title: "{clean_title}"'

    if os.path.isfile(anno_file):
        try:
            with open(anno_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            m = re.search(r'title\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', content)
            if m:
                existing_t = m.group(1).strip()
                if not existing_t or existing_t in ["Conversation", "Untitled Conversation"]:
                    new_content = re.sub(r'title\s*:\s*"[^"\\]*(?:\\.[^"\\]*)*"', title_line, content)
                    with open(anno_file, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    return True
            else:
                new_content = f"{title_line}  {content}".strip()
                with open(anno_file, "w", encoding="utf-8") as f:
                    f.write(f"{new_content}\n")
                return True
        except Exception:
            return False
    else:
        try:
            with open(anno_file, "w", encoding="utf-8") as f:
                f.write(f"{title_line}\n")
            return True
        except Exception:
            return False
    return False


def extract_conv_text(
    db_path: Union[str, Path],
    transcript_path: Union[str, Path],
) -> Tuple[str, str]:
    """Extracts (title, preview) from transcript, artifacts, and sqlite steps."""
    first_user_prompt = ""
    latest_user_prompt = ""

    t_candidates = []
    t_str = str(transcript_path) if transcript_path else ""
    if t_str:
        t_candidates.append(t_str)
        if "transcript.jsonl" in t_str:
            t_candidates.insert(0, t_str.replace("transcript.jsonl", "transcript_full.jsonl"))

    for tf in t_candidates:
        if os.path.isfile(tf):
            try:
                with open(tf, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except Exception:
                            continue
                        src = entry.get("source", "")
                        typ = entry.get("type", "")
                        content = entry.get("content", "")
                        if typ == "USER_INPUT" or (src == "USER_EXPLICIT" and typ not in ["VIEW_FILE", "CODE_ACTION"]):
                            clean = content
                            m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                            if m:
                                clean = m.group(1).strip()
                            else:
                                clean = content.strip()
                            if clean:
                                if not first_user_prompt:
                                    first_user_prompt = clean
                                latest_user_prompt = clean
                if first_user_prompt:
                    break
            except Exception:
                pass

    # Inspect SQLite database if transcript was not enough
    db_str = str(db_path) if db_path else ""
    if not first_user_prompt and os.path.isfile(db_str):
        try:
            conn = sqlite3.connect(db_str)
            cur = conn.cursor()
            cur.execute("SELECT step_payload FROM steps WHERE step_type = 14 ORDER BY idx ASC LIMIT 5;")
            rows = cur.fetchall()
            for r in rows:
                if r[0]:
                    parsed = parse_step14_user_prompt(r[0])
                    if parsed:
                        if not first_user_prompt:
                            first_user_prompt = parsed
                        latest_user_prompt = parsed
            conn.close()
        except Exception:
            pass

    # Inspect markdown artifacts in the brain folder
    if t_str:
        brain_folder = os.path.dirname(os.path.dirname(os.path.dirname(t_str)))
        if os.path.isdir(brain_folder):
            for art_name in ["task.md", "implementation_plan.md", "architecture.md"]:
                art_file = os.path.join(brain_folder, art_name)
                if os.path.isfile(art_file):
                    try:
                        with open(art_file, "r", encoding="utf-8", errors="ignore") as af:
                            for l in af:
                                l_clean = l.strip()
                                if l_clean.startswith("# ") and len(l_clean) > 3:
                                    art_title = l_clean[2:].strip()
                                    if art_title and art_title not in ["Task", "Implementation Plan"]:
                                        return art_title, latest_user_prompt or first_user_prompt or art_title
                    except Exception:
                        pass
            # Any markdown file with a heading
            for af_path in glob.glob(os.path.join(brain_folder, "*.md")):
                try:
                    with open(af_path, "r", encoding="utf-8", errors="ignore") as af:
                        for l in af:
                            l_clean = l.strip()
                            if l_clean.startswith("# ") and len(l_clean) > 3:
                                art_title = l_clean[2:].strip()
                                if art_title and art_title not in ["Task", "Overview"]:
                                    return art_title, latest_user_prompt or first_user_prompt or art_title
                except Exception:
                    pass

    title = ""
    preview = latest_user_prompt or first_user_prompt or ""
    if first_user_prompt:
        lines = [line.strip() for line in first_user_prompt.split("\n") if line.strip()]
        if lines:
            t_cand = lines[0]
            if len(t_cand) > 80:
                t_cand = t_cand[:77] + "..."
            title = t_cand

    return title, preview
