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
from typing import Dict, Optional, Set, Tuple, Union

from antigravity_suite.history.synthesizer import parse_step14_user_prompt
from antigravity_suite.proto.wire import read_varint


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


def is_clean_title(val: Optional[str]) -> bool:
    """Returns True if the string is an authentic, human-readable conversation title."""
    if not val or not isinstance(val, str):
        return False
    s = val.strip()
    if not s or s in ["Conversation", "IDE Conversation", "Untitled Conversation", "---"]:
        return False
    if len(s) < 2:
        return False
    if s.startswith(("@[", "{", "}", "[", "]", "<USER_REQUEST>", "<ADDITIONAL_METADATA>", "```", "<?php", "#!", "/*")):
        return False
    if not any(c.isalnum() for c in s):
        return False
    # Check for terminal/shell prompt indicators like ╰─❯, ❯, $, #, root@..., user@host...
    if re.match(r"^(?:[╰╭│├└─\s]*[❯>$#%]\s*|root@[^:]+:[^\s#$]+[#$]\s*|[a-zA-Z0-9_-]+@[^:]+:[^\s#$]+[#$]\s*)", s):
        return False
    # Check for raw terminal/CLI command lines, code blocks, or URLs
    if s.startswith(("curl ", "docker ", "git ", "ssh ", "sudo ", "cd ", "npm ", "cat ", "ls ", "export ", "bash ", "python ", "systemctl ", "journalctl ", "grep ", "http://", "https://", "import ", "def ", "class ", "return ")):
        return False
    return True


def get_annotation_title(gemini_dir: Union[str, Path], conv_id: str) -> Optional[str]:
    """Reads authentic title from annotations/<conv_id>.pbtxt if present."""
    return get_annotation_info(gemini_dir, conv_id).get("title")


def sync_annotation_file(
    master_gemini: Union[str, Path],
    conv_id: str,
    title: str,
    pinned: Optional[bool] = None,
    archived: Optional[bool] = None,
    force: bool = False,
) -> bool:
    """Ensures annotations/<conv_id>.pbtxt exists, has valid title, and preserves pinned/archived states."""
    anno_dir = os.path.join(str(master_gemini), "annotations")
    os.makedirs(anno_dir, exist_ok=True)
    anno_file = os.path.join(anno_dir, f"{conv_id}.pbtxt")

    clean_title = re.sub(r"(?:in\s*)?@\[[^\]]+\]", "", title or "").strip()
    clean_title = clean_title.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    is_valid_title = is_clean_title(clean_title) and clean_title not in ["Conversation", "Untitled Conversation"]

    existing_content = ""
    if os.path.isfile(anno_file):
        try:
            with open(anno_file, "r", encoding="utf-8", errors="ignore") as f:
                existing_content = f.read()
        except Exception:
            pass

    existing_t = ""
    m = re.search(r'title\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', existing_content)
    if m:
        existing_t = m.group(1).strip()

    is_pinned = pinned
    if is_pinned is None:
        is_pinned = bool(re.search(r'pinned\s*:\s*true', existing_content, re.IGNORECASE))

    is_archived = archived
    if is_archived is None:
        is_archived = bool(re.search(r'archived\s*:\s*true', existing_content, re.IGNORECASE))

    final_t = ""
    if is_valid_title:
        if force or not existing_t or not is_clean_title(existing_t):
            final_t = clean_title
        else:
            final_t = existing_t
    elif existing_t and is_clean_title(existing_t) and existing_t not in ["Conversation", "Untitled Conversation"]:
        final_t = existing_t

    extra_fields = []
    for extra in re.findall(r'(last_user_view_time\s*:\s*\{[^}]*\})', existing_content):
        extra_fields.append(extra.strip())

    if not final_t and not is_pinned and not is_archived and not extra_fields:
        if os.path.isfile(anno_file):
            try:
                os.remove(anno_file)
                return True
            except Exception:
                pass
        return False

    lines = []
    if final_t:
        lines.append(f'title: "{final_t}"')
    if is_pinned:
        lines.append("pinned:true")
    if is_archived:
        lines.append("archived:true")
    for extra in extra_fields:
        lines.append(extra)

    # Check if logically equivalent before touching disk to avoid triggering Language Server annotation watcher
    existing_pinned = bool(re.search(r'pinned\s*:\s*true', existing_content, re.IGNORECASE))
    existing_archived = bool(re.search(r'archived\s*:\s*true', existing_content, re.IGNORECASE))
    if existing_content and existing_t == final_t and existing_pinned == bool(is_pinned) and existing_archived == bool(is_archived):
        return False

    new_content = "\n".join(lines) + "\n"
    if new_content != existing_content:
        try:
            with open(anno_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True
        except Exception:
            return False
    return False


_EXTRACT_CACHE: Dict[Tuple[str, int, int, str, int, int], Tuple[str, str]] = {}
_PROMPT_CACHE: Dict[Tuple[str, int, int, str, int, int], Set[str]] = {}


def _get_file_stat(p: Union[str, Path, None]) -> Tuple[int, int]:
    if not p:
        return (0, 0)
    try:
        st = os.stat(str(p))
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return (0, 0)


def extract_conv_prompts(
    db_path: Union[str, Path, None],
    transcript_path: Union[str, Path, None],
) -> Set[str]:
    """
    Extracts all user prompt text variants across DB steps and transcript logs
    to prevent raw prompts from ever being treated as conversation titles.
    """
    db_key = str(db_path) if db_path else ""
    tr_key = str(transcript_path) if transcript_path else ""
    stat_db = _get_file_stat(db_path)
    stat_tr = _get_file_stat(transcript_path)
    cache_key = (db_key, stat_db[0], stat_db[1], tr_key, stat_tr[0], stat_tr[1])
    if cache_key in _PROMPT_CACHE:
        return set(_PROMPT_CACHE[cache_key])

    prompts: Set[str] = set()

    # 1. From transcript
    t_str = str(transcript_path) if transcript_path else ""
    if t_str and os.path.isfile(t_str):
        try:
            with open(t_str, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
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

    # 2. From SQLite steps table
    db_str = str(db_path) if db_path else ""
    if db_str and os.path.isfile(db_str):
        conn = None
        try:
            conn = sqlite3.connect(db_str, timeout=10.0)
            cur = conn.cursor()
            cur.execute("SELECT step_payload FROM steps WHERE step_type = 14;")
            for r in cur.fetchall():
                if r[0]:
                    p = parse_step14_user_prompt(r[0])
                    if p and p.strip():
                        prompts.add(p.strip())
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
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
                    sh_clean = re.sub(
                        r"^(?:[╰╭│├└─\s]*[❯>$#%]\s*|root@[^:]+:[^\s#$]+[#$]\s*|[a-zA-Z0-9_-]+@[^:]+:[^\s#$]+[#$]\s*)",
                        "",
                        l_strip,
                    ).strip()
                    if sh_clean:
                        signatures.add(sh_clean)
            for length in [60, 77, 80, 100]:
                if len(space_clean) >= length:
                    signatures.add(space_clean[:length].strip())

    _PROMPT_CACHE[cache_key] = signatures
    return signatures


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


def parse_step23_checkpoint_title(payload: bytes) -> Optional[str]:
    """Extracts authentic checkpoint title (Tag 30 -> Tag 4) from step_type = 23 binary payload."""
    if not payload:
        return None
    pos = 0
    data_len = len(payload)
    while pos < data_len:
        tw, pos = read_varint(payload, pos)
        wt = tw & 7
        tag = tw >> 3
        if wt == 2:
            l, pos = read_varint(payload, pos)
            val = payload[pos : pos + l]
            pos += l
            if tag == 30:
                p30 = 0
                val_len = len(val)
                while p30 < val_len:
                    tw30, p30 = read_varint(val, p30)
                    wt30 = tw30 & 7
                    tag30 = tw30 >> 3
                    if wt30 == 2:
                        l30, p30 = read_varint(val, p30)
                        v30 = val[p30 : p30 + l30]
                        p30 += l30
                        if tag30 == 4:
                            try:
                                cand = v30.decode("utf-8", errors="ignore").strip()
                                if cand and is_clean_title(cand):
                                    return cand
                            except Exception:
                                pass
                    elif wt30 == 0:
                        _, p30 = read_varint(val, p30)
                    elif wt30 == 1:
                        p30 += 8
                    elif wt30 == 5:
                        p30 += 4
                    else:
                        break
        elif wt == 0:
            _, pos = read_varint(payload, pos)
        elif wt == 1:
            pos += 8
        elif wt == 5:
            pos += 4
        else:
            break
    return None


def extract_conv_text(
    db_path: Union[str, Path],
    transcript_path: Union[str, Path],
) -> Tuple[str, str]:
    """Extracts (title, preview) from transcript, artifacts, and sqlite steps."""
    db_stat = _get_file_stat(db_path)
    tr_stat = _get_file_stat(transcript_path)
    cache_key = (
        str(db_path) if db_path else "",
        db_stat[0],
        db_stat[1],
        str(transcript_path) if transcript_path else "",
        tr_stat[0],
        tr_stat[1],
    )
    if cache_key in _EXTRACT_CACHE:
        return _EXTRACT_CACHE[cache_key]

    first_user_prompt = ""
    latest_user_prompt = ""

    t_candidates = []
    t_str = str(transcript_path) if transcript_path else ""
    if t_str:
        if "transcript_full.jsonl" in t_str:
            t_candidates.append(t_str)
            t_short = t_str.replace("transcript_full.jsonl", "transcript.jsonl")
            if os.path.isfile(t_short):
                t_candidates.insert(0, t_short)
        else:
            t_candidates.append(t_str)
            t_full = t_str.replace("transcript.jsonl", "transcript_full.jsonl")
            if not os.path.isfile(t_str) and os.path.isfile(t_full):
                t_candidates.append(t_full)

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

    # Inspect SQLite database for authentic checkpoint title and user prompts
    checkpoint_title = ""
    db_str = str(db_path) if db_path else ""
    if os.path.isfile(db_str):
        conn = None
        try:
            conn = sqlite3.connect(db_str, timeout=15.0)
            cur = conn.cursor()

            # Check for authentic CORTEX_STEP_TYPE_CHECKPOINT (step_type = 23 -> Tag 30 -> Tag 4)
            try:
                cur.execute("SELECT step_payload FROM steps WHERE step_type = 23 ORDER BY idx DESC LIMIT 5;")
                for cp_row in cur.fetchall():
                    if cp_row and cp_row[0]:
                        t_cand = parse_step23_checkpoint_title(cp_row[0])
                        if t_cand:
                            checkpoint_title = t_cand
                            break
            except Exception:
                pass

            if not first_user_prompt or not latest_user_prompt:
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
    title = checkpoint_title or ""
    if not title and brain_folder and os.path.isdir(brain_folder):
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

    preview = latest_user_prompt or first_user_prompt or ""

    res = (title, preview)
    if len(_EXTRACT_CACHE) > 5000:
        _EXTRACT_CACHE.clear()
    _EXTRACT_CACHE[cache_key] = res
    return res
