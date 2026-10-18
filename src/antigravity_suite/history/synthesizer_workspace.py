"""
Transcript Workspace URI Extraction.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional, Union
from urllib.parse import unquote, urlsplit

from antigravity_suite.config import get_user_home


def extract_workspace_from_transcript(
    transcript_path: Union[str, Path],
    project_id: Optional[str] = None,
    user_home: Optional[Path] = None,
) -> Optional[str]:
    """Extracts authentic, validated workspace URI from project config or transcript logs."""
    from antigravity_suite.history.projects import get_workspace_for_project_id, is_valid_workspace_uri, normalize_workspace_uri

    home = user_home or get_user_home()
    if project_id and str(project_id).strip() not in ("outside-of-project", "default-cli-project"):
        proj_ws = get_workspace_for_project_id(str(project_id).strip(), user_home=home)
        if proj_ws and is_valid_workspace_uri(proj_ws, user_home=home):
            return proj_ws

    tf_str = str(transcript_path)
    if not os.path.isfile(tf_str):
        return None

    try:
        with open(tf_str, "r", encoding="utf-8", errors="ignore") as tf_f:
            for line_idx, line in enumerate(tf_f):
                if line_idx > 300:
                    break
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue

                content = entry.get("content", "")
                if isinstance(content, str) and content:
                    for header in ["Active Workspaces:\\s*(?:\\n|\\r\\n)?\\s*[-*]\\s*([^\\s\\n\\r`\"'>]+)",
                                   "Command Working Directory:\\s*([^\\s\\n\\r`\"'>]+)"]:
                        m = re.search(header, content)
                        if m:
                            cand = m.group(1).strip().rstrip("`\"';,")
                            norm = normalize_workspace_uri(cand if cand.startswith("file://") else ("file://" + cand), user_home=home)
                            if is_valid_workspace_uri(norm, user_home=home):
                                return norm

                tool_calls = entry.get("tool_calls", [])
                if isinstance(tool_calls, list):
                    for tc in tool_calls:
                        args = tc.get("args") or {}
                        if isinstance(args, dict):
                            cwd = args.get("Cwd")
                            if cwd and isinstance(cwd, str) and os.path.isdir(cwd.strip().rstrip("`\"';,")):
                                norm = normalize_workspace_uri("file://" + cwd.strip().rstrip("`\"';,"), user_home=home)
                                if is_valid_workspace_uri(norm, user_home=home):
                                    return norm
                            for k in ("AbsolutePath", "TargetFile"):
                                fp = args.get(k)
                                if fp and isinstance(fp, str):
                                    clean_p = unquote(urlsplit(fp).path) if fp.startswith("file://") else fp.strip('"`\'')
                                    p_dir = clean_p if os.path.isdir(clean_p) else os.path.dirname(clean_p)
                                    if os.path.isdir(p_dir):
                                        norm = normalize_workspace_uri("file://" + p_dir, user_home=home)
                                        if is_valid_workspace_uri(norm, user_home=home):
                                            return norm
    except Exception:
        pass
    return None
