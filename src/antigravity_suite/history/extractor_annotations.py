"""
Annotation File (.pbtxt) Parsing and Synchronization.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional, Union

from antigravity_suite.history.extractor_cleaners import is_clean_title
from antigravity_suite.history.extractor_pbtxt import decode_pbtxt_string


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
    master_gemini: Union[str, Path], conv_id: str, title: str,
    pinned: Optional[bool] = None, archived: Optional[bool] = None, force: bool = False,
) -> bool:
    """Ensures annotations/<conv_id>.pbtxt exists, has valid title, and preserves pinned/archived states."""
    anno_dir = os.path.join(str(master_gemini), "annotations")
    os.makedirs(anno_dir, exist_ok=True)
    anno_file = os.path.join(anno_dir, f"{conv_id}.pbtxt")

    clean_t = re.sub(r"(?:in\s*)?@\[[^\]]+\]", "", title or "").strip().replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    is_valid = is_clean_title(clean_t) and clean_t not in ["Conversation", "Untitled Conversation"]
    existing_content = ""
    if os.path.isfile(anno_file):
        try:
            with open(anno_file, "r", encoding="utf-8", errors="ignore") as f:
                existing_content = f.read()
        except Exception:
            pass

    m = re.search(r'title\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', existing_content)
    existing_t = m.group(1).strip() if m else ""
    is_pin = pinned if pinned is not None else bool(re.search(r'pinned\s*:\s*true', existing_content, re.IGNORECASE))
    is_arc = archived if archived is not None else bool(re.search(r'archived\s*:\s*true', existing_content, re.IGNORECASE))
    final_t = clean_t if (is_valid and (force or not existing_t or not is_clean_title(existing_t))) else (existing_t if (existing_t and is_clean_title(existing_t) and existing_t not in ["Conversation", "Untitled Conversation"]) else "")

    extra = [x.strip() for x in re.findall(r'(last_user_view_time\s*:\s*\{[^}]*\})', existing_content)]
    if not final_t and not is_pin and not is_arc and not extra:
        if os.path.isfile(anno_file):
            try:
                os.remove(anno_file)
                return True
            except Exception:
                pass
        return False

    lines = ([f'title: "{final_t}"'] if final_t else []) + (["pinned:true"] if is_pin else []) + (["archived:true"] if is_arc else []) + extra
    new_content = "\n".join(lines) + "\n"
    if new_content != existing_content:
        try:
            with open(anno_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True
        except Exception:
            return False
    return False
