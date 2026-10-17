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

from antigravity_suite.history.synthesizer import parse_step14_user_prompt


def decode_pbtxt_string(s: str) -> str:
    """Decodes a Protobuf text format quoted string, preserving UTF-8 text and resolving escape sequences."""
    if not s:
        return ""
    if "\\" not in s:
        return s.strip()

    # 1. Decode consecutive octal byte escapes (Protobuf text format for UTF-8 bytes: e.g. \330\263)
    def decode_octal_match(m: re.Match) -> str:
        raw_bytes = bytes(int(x, 8) for x in re.findall(r"\\([0-7]{1,3})", m.group(0)))
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return raw_bytes.decode("latin-1", errors="replace")

    res = re.sub(r"(?:\\[0-7]{1,3})+", decode_octal_match, s)

    # 2. Decode standard unicode escapes (\uXXXX, \UXXXXXXXX) and common C escapes
    if "\\" in res:
        try:
            res = re.sub(
                r"\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}",
                lambda m: m.group(0).encode("utf-8").decode("unicode_escape"),
                res,
            )
            def _unescape_c(m: re.Match) -> str:
                esc_map = {
                    "n": "\n",
                    "r": "\r",
                    "t": "\t",
                    '"': '"',
                    "'": "'",
                    "\\": "\\",
                }
                char = m.group(1)
                return esc_map.get(char, m.group(0))

            res = re.sub(r'\\([nrt"\'\\])', _unescape_c, res)
        except Exception:
            pass

    return res.strip()


def get_annotation_info(gemini_dir: Union[str, Path], conv_id: str) -> dict:
    """Reads authentic title, pinned, and archived status from annotations/<conv_id>.pbtxt."""
    anno_file = os.path.join(str(gemini_dir), "annotations", f"{conv_id}.pbtxt")
    info = {"title": None, "pinned": None, "archived": None, "exists": False}
    if os.path.isfile(anno_file):
        info["exists"] = True
        try:
            with open(anno_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            m = re.search(r'title\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', content)
            if m:
                clean_title = decode_pbtxt_string(m.group(1))
                if clean_title and clean_title not in ["Conversation", "Untitled Conversation"] and "@[" not in clean_title:
                    info["title"] = clean_title
            if re.search(r'pinned\s*:\s*true', content, re.IGNORECASE):
                info["pinned"] = True
            elif re.search(r'pinned\s*:\s*false', content, re.IGNORECASE):
                info["pinned"] = False

            if re.search(r'archived\s*:\s*true', content, re.IGNORECASE):
                info["archived"] = True
            elif re.search(r'archived\s*:\s*false', content, re.IGNORECASE):
                info["archived"] = False
        except Exception:
            pass
    return info


def get_annotation_title(gemini_dir: Union[str, Path], conv_id: str) -> Optional[str]:
    """Reads authentic title from annotations/<conv_id>.pbtxt if present."""
    return get_annotation_info(gemini_dir, conv_id).get("title")


def sync_annotation_file(
    master_gemini: Union[str, Path],
    conv_id: str,
    title: str,
    pinned: Optional[bool] = None,
    archived: Optional[bool] = None,
) -> bool:
    """Ensures annotations/<conv_id>.pbtxt exists, has title, and preserves pinned/archived states."""
    if not title or title.strip() in ["", "Conversation", "Untitled Conversation"]:
        return False

    anno_dir = os.path.join(str(master_gemini), "annotations")
    os.makedirs(anno_dir, exist_ok=True)
    anno_file = os.path.join(anno_dir, f"{conv_id}.pbtxt")

    clean_title = re.sub(r"(?:in\s*)?@\[[^\]]+\]", "", title).strip()
    clean_title = clean_title.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    if not clean_title or clean_title in ["", "Conversation", "Untitled Conversation"]:
        clean_title = "Conversation"
    title_line = f'title: "{clean_title}"'

    if os.path.isfile(anno_file):
        try:
            with open(anno_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            m = re.search(r'title\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', content)
            if m:
                existing_t = m.group(1).strip()
                if not existing_t or existing_t in ["Conversation", "Untitled Conversation"] or "@[" in existing_t:
                    new_content = re.sub(r'title\s*:\s*"[^"\\]*(?:\\.[^"\\]*)*"', title_line, content)
                else:
                    new_content = content
            else:
                new_content = f"{title_line}  {content}".strip()

            if pinned is True:
                if not re.search(r'pinned\s*:\s*true', new_content, re.IGNORECASE):
                    new_content = new_content.strip() + "  pinned:true"
            elif pinned is False:
                new_content = re.sub(r'\s*pinned\s*:\s*true', '', new_content, flags=re.IGNORECASE)

            if archived is True:
                if not re.search(r'archived\s*:\s*true', new_content, re.IGNORECASE):
                    new_content = new_content.strip() + "  archived:true"
            elif archived is False:
                new_content = re.sub(r'\s*archived\s*:\s*true', '', new_content, flags=re.IGNORECASE)

            new_content = re.sub(r'[ \t]+', ' ', new_content).strip()

            if new_content != content.strip():
                with open(anno_file, "w", encoding="utf-8") as f:
                    f.write(f"{new_content}\n")
                return True
        except Exception:
            return False
    else:
        try:
            body = title_line
            if pinned is True:
                body += "  pinned:true"
            if archived is True:
                body += "  archived:true"
            with open(anno_file, "w", encoding="utf-8") as f:
                f.write(f"{body}\n")
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
                        try:
                            src = entry.get("source", "")
                            typ = entry.get("type", "")
                            content = entry.get("content", "")
                            if not isinstance(content, str):
                                continue
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
                        except Exception:
                            continue
                if first_user_prompt:
                    break
            except Exception:
                pass

    # Inspect SQLite database if transcript was not enough
    db_str = str(db_path) if db_path else ""
    if not first_user_prompt and os.path.isfile(db_str):
        conn = None
        try:
            conn = sqlite3.connect(db_str, timeout=15.0)
            cur = conn.cursor()
            # First prompt for title
            cur.execute("SELECT step_payload FROM steps WHERE step_type = 14 ORDER BY idx ASC LIMIT 1;")
            f_row = cur.fetchone()
            if f_row and f_row[0]:
                first_user_prompt = parse_step14_user_prompt(f_row[0]) or ""

            # Latest prompt for preview
            cur.execute("SELECT step_payload FROM steps WHERE step_type = 14 ORDER BY idx DESC LIMIT 1;")
            l_row = cur.fetchone()
            if l_row and l_row[0]:
                latest_user_prompt = parse_step14_user_prompt(l_row[0]) or ""
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    # Brain folder resolution (from transcript or sqlite db path)
    generic_blacklist = {
        "task", "tasks", "implementation plan", "overview", "walkthrough",
        "architecture", "notes", "summary", "checklist", "test results",
        "verification", "instructions", "scratchpad", "conversation", "untitled conversation"
    }

    brain_folder = ""
    if t_str:
        cand_bf = os.path.dirname(os.path.dirname(os.path.dirname(t_str)))
        conv_uuid = os.path.basename(cand_bf)
        parent_dir = os.path.dirname(cand_bf)
        # Check direct folder
        if os.path.isdir(cand_bf) and any(glob.glob(os.path.join(cand_bf, "*.md"))):
            brain_folder = cand_bf
        else:
            # Check sibling brain/<conv_id> or antigravity/brain/<conv_id>
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
        cand_bf = str(p_db.parent.parent / "brain" / p_db.stem)
        if os.path.isdir(cand_bf):
            brain_folder = cand_bf
        else:
            cand_bf2 = str(p_db.parent.parent.parent / "brain" / p_db.stem)
            if os.path.isdir(cand_bf2):
                brain_folder = cand_bf2

    # 1. Authentic H1 Document Title Extraction Pipeline (SKILL.md 7.3)
    title = ""
    if brain_folder and os.path.isdir(brain_folder):
        for art_name in ["task.md", "implementation_plan.md", "architecture.md"]:
            art_file = os.path.join(brain_folder, art_name)
            if os.path.isfile(art_file):
                try:
                    with open(art_file, "r", encoding="utf-8", errors="ignore") as af:
                        for l in af:
                            l_clean = l.strip()
                            if l_clean.startswith("# ") and len(l_clean) > 3:
                                art_title = l_clean[2:].strip()
                                if art_title and art_title.lower() not in generic_blacklist:
                                    title = art_title
                                    break
                except Exception:
                    pass
            if title:
                break
        if not title:
            for af_path in glob.glob(os.path.join(brain_folder, "*.md")):
                try:
                    with open(af_path, "r", encoding="utf-8", errors="ignore") as af:
                        for l in af:
                            l_clean = l.strip()
                            if l_clean.startswith("# ") and len(l_clean) > 3:
                                art_title = l_clean[2:].strip()
                                if art_title and art_title.lower() not in generic_blacklist:
                                    title = art_title
                                    break
                except Exception:
                    pass
                if title:
                    break

    # 2. Prompt Fallback: if no authentic H1 title could be derived from artifacts
    preview = latest_user_prompt or first_user_prompt or ""
    if not title and first_user_prompt:
        clean_first = re.sub(r"(?:in\s*)?@\[[^\]]+\]", "", first_user_prompt).strip()
        lines = [line.strip() for line in clean_first.split("\n") if line.strip()]
        if not lines and latest_user_prompt:
            clean_latest = re.sub(r"(?:in\s*)?@\[[^\]]+\]", "", latest_user_prompt).strip()
            lines = [line.strip() for line in clean_latest.split("\n") if line.strip()]
        if not lines:
            lines = [line.strip() for line in first_user_prompt.split("\n") if line.strip()]

        if lines:
            t_cand = lines[0]
            if len(t_cand) > 80:
                t_cand = t_cand[:77] + "..."
            if t_cand and t_cand.lower() not in ["hi", "hello", "hey", "conversation", "untitled conversation"]:
                title = t_cand

    if not preview and title:
        preview = title

    return title, preview
