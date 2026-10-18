"""
High-Fidelity SQLite Conversation Database Synthesizer.

Reconstructs valid SQLite databases from JSON Lines transcripts (transcript.jsonl /
transcript_full.jsonl), restoring full Protobuf message payloads, user prompts,
assistant reasoning, tool execution parameters, and workspace metadata.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from antigravity_suite.config import DEFAULT_CONFIG, get_user_home
from antigravity_suite.proto.trajectory import build_trajectory_metadata_blob
from antigravity_suite.proto.wire import encode_tag_bytes, encode_tag_uint, read_varint


def _has_tag_in_proto(data: bytes, target_tag: int, target_wire: int = 2) -> bool:
    """Checks whether a valid protobuf tag exists at the top level of serialized bytes."""
    if not data:
        return False
    pos = 0
    d_len = len(data)
    while pos < d_len:
        try:
            tag_wire, pos = read_varint(data, pos)
            wire_type = tag_wire & 7
            tag_num = tag_wire >> 3
            if wire_type == 0:
                _, pos = read_varint(data, pos)
            elif wire_type == 1:
                pos += 8
            elif wire_type == 5:
                pos += 4
            elif wire_type == 2:
                length, pos = read_varint(data, pos)
                if pos + length > d_len:
                    break
                if tag_num == target_tag and wire_type == target_wire and length > 0:
                    return True
                pos += length
            else:
                break
        except Exception:
            break
    return False


_VERIFIED_COMPLETE_DBS: Dict[str, Tuple[float, int]] = {}  # db_p -> (mtime, size)


def clear_synthesized_db_cache() -> None:
    """Clears the verified complete database cache."""
    _VERIFIED_COMPLETE_DBS.clear()


def is_synthesized_db_incomplete(db_path: Union[str, Path]) -> bool:
    """
    Checks if a conversation SQLite database has missing/empty message payloads
    (e.g. legacy synthesized databases missing Tag 20 assistant messages or Step 132 tool metadata).
    STRICTLY protects authentic databases containing rich step types from ever being re-synthesized.
    Uses compound stat caching (db_p, mtime, size) to eliminate hundreds of redundant SQLite inspection queries.
    """
    db_p = str(db_path)
    try:
        st = os.stat(db_p)
    except Exception:
        return True

    mtime = st.st_mtime
    size = st.st_size
    if size == 0:
        return True

    cached = _VERIFIED_COMPLETE_DBS.get(db_p)
    if cached is not None and cached[0] == mtime and cached[1] == size:
        return False

    conn = None
    try:
        conn = sqlite3.connect(db_p, timeout=15.0)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM steps;")
        total_steps = cur.fetchone()[0]
        if total_steps == 0:
            return True

        # Check step types: if authentic rich step types exist, protect completely!
        cur.execute("SELECT DISTINCT step_type FROM steps;")
        step_types = {r[0] for r in cur.fetchall()}
        rich_authentic_types = step_types - {0, 14, 15, 132}
        if rich_authentic_types:
            _VERIFIED_COMPLETE_DBS[db_p] = (mtime, size)
            return False

        # Step 14 check: ensure user prompt bubble and Tag 3 chunk are present
        cur.execute("SELECT step_payload FROM steps WHERE step_type = 14 LIMIT 5;")
        s14_rows = cur.fetchall()
        if s14_rows:
            has_valid_user = any(row[0] and bool(parse_step14_user_prompt(row[0])) for row in s14_rows)
            if not has_valid_user:
                return True

        # Step 15 check: assistant text in Tag 20
        cur.execute("SELECT step_payload FROM steps WHERE step_type = 15 LIMIT 5;")
        s15_rows = cur.fetchall()
        if s15_rows:
            has_tag20 = any(row[0] and _has_tag_in_proto(row[0], 20, 2) for row in s15_rows)
            if not has_tag20:
                return True

        # Step 132 check: verify tool execution metadata (Tag 4) and tool payload (Tag 140)
        cur.execute("SELECT metadata, step_payload FROM steps WHERE step_type = 132 LIMIT 5;")
        s132_rows = cur.fetchall()
        if s132_rows:
            has_tool_meta = any(row[0] and _has_tag_in_proto(row[0], 4, 2) for row in s132_rows)
            has_tool_payload = any(row[1] and _has_tag_in_proto(row[1], 140, 2) for row in s132_rows)
            if not (has_tool_meta and has_tool_payload):
                return True

        _VERIFIED_COMPLETE_DBS[db_p] = (mtime, size)
        return False
    except Exception:
        return True
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def parse_step14_user_prompt(payload: bytes) -> str:
    """
    Extracts authentic user prompt text from Step 14 payload:
      Tag 19 (length-delimited):
        Tag 2 (string): clean user message
        Tag 3 (submessage):
          Tag 1 (string): chunk content
    """
    if not payload:
        return ""
    pos = 0
    p_len = len(payload)
    clean_text = ""
    chunk_text = ""

    while pos < p_len:
        tag_wire, pos = read_varint(payload, pos)
        wire_type = tag_wire & 7
        tag_num = tag_wire >> 3

        if wire_type == 2:
            length, pos = read_varint(payload, pos)
            val = payload[pos : pos + length]
            pos += length

            if tag_num == 19:
                p19 = 0
                while p19 < len(val):
                    tw19, p19 = read_varint(val, p19)
                    w19 = tw19 & 7
                    t19 = tw19 >> 3
                    if w19 == 2:
                        l19, p19 = read_varint(val, p19)
                        v19 = val[p19 : p19 + l19]
                        p19 += l19
                        if t19 == 2:
                            try:
                                clean_text = v19.decode("utf-8", errors="ignore")
                            except Exception:
                                pass
                        elif t19 == 3:
                            p_chunk = 0
                            while p_chunk < len(v19):
                                tw_c, p_chunk = read_varint(v19, p_chunk)
                                w_c = tw_c & 7
                                if w_c == 2:
                                    lc, p_chunk = read_varint(v19, p_chunk)
                                    vc = v19[p_chunk : p_chunk + lc]
                                    p_chunk += lc
                                    if (tw_c >> 3) == 1:
                                        try:
                                            chunk_text = vc.decode("utf-8", errors="ignore")
                                        except Exception:
                                            pass
                                elif w_c == 0:
                                    _, p_chunk = read_varint(v19, p_chunk)
                                elif w_c == 1:
                                    p_chunk += 8
                                elif w_c == 5:
                                    p_chunk += 4
                                else:
                                    break
                    elif w19 == 0:
                        _, p19 = read_varint(val, p19)
                    elif w19 == 1:
                        p19 += 8
                    elif w19 == 5:
                        p19 += 4
                    else:
                        break
        elif wire_type == 0:
            _, pos = read_varint(payload, pos)
        elif wire_type == 1:
            pos += 8
        elif wire_type == 5:
            pos += 4
        else:
            break

    raw_res = clean_text or chunk_text
    m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", raw_res, re.DOTALL)
    if m:
        return m.group(1).strip()
    return raw_res.strip()


def extract_workspace_from_transcript(
    transcript_path: Union[str, Path],
    project_id: Optional[str] = None,
    user_home: Optional[Path] = None,
) -> Optional[str]:
    """
    Extracts authentic, validated workspace URI from project configuration,
    transcript logs, or tool execution directories.
    """
    from antigravity_suite.history.projects import (
        get_workspace_for_project_id,
        is_valid_workspace_uri,
        normalize_workspace_uri,
    )
    from urllib.parse import urlsplit, unquote

    home = user_home or get_user_home()

    # 1. Authoritative project configuration lookup
    if project_id and str(project_id).strip() not in ("outside-of-project", "default-cli-project"):
        proj_ws = get_workspace_for_project_id(str(project_id).strip(), user_home=home)
        if proj_ws and is_valid_workspace_uri(proj_ws, user_home=home):
            return proj_ws

    tf_str = str(transcript_path)
    if not os.path.isfile(tf_str):
        return None

    # 2. Parse transcript JSON entries (scan first 300 entries)
    try:
        with open(tf_str, "r", encoding="utf-8", errors="ignore") as tf_f:
            for line_idx, line in enumerate(tf_f):
                if line_idx > 300:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue

                content = entry.get("content", "")
                if isinstance(content, str) and content:
                    # Look for explicit system prompt headers
                    if "Active Workspaces:" in content:
                        m = re.search(r"Active Workspaces:\s*(?:\n|\r\n)?\s*[-*]\s*([^\s\n\r`\"'>]+)", content)
                        if m:
                            cand = m.group(1).strip().rstrip("`\"';,")
                            cand_uri = cand if cand.startswith("file://") else ("file://" + cand)
                            norm = normalize_workspace_uri(cand_uri, user_home=home)
                            if is_valid_workspace_uri(norm, user_home=home):
                                return norm

                    if "Command Working Directory:" in content:
                        m = re.search(r"Command Working Directory:\s*([^\s\n\r`\"'>]+)", content)
                        if m:
                            cand = m.group(1).strip().rstrip("`\"';,")
                            cand_uri = cand if cand.startswith("file://") else ("file://" + cand)
                            norm = normalize_workspace_uri(cand_uri, user_home=home)
                            if is_valid_workspace_uri(norm, user_home=home):
                                return norm

                    if "Active Document:" in content:
                        m = re.search(r"Active Document:\s*([^\s\n\r`\"'>]+)", content)
                        if m:
                            doc_p = m.group(1).strip().rstrip("`\"';,")
                            doc_p = unquote(urlsplit(doc_p).path) if doc_p.startswith("file://") else doc_p
                            parent_dir = os.path.dirname(doc_p)
                            if os.path.isdir(parent_dir):
                                norm = normalize_workspace_uri("file://" + parent_dir, user_home=home)
                                if is_valid_workspace_uri(norm, user_home=home):
                                    return norm

                # Inspect tool calls for authentic working directory
                tool_calls = entry.get("tool_calls", [])
                if isinstance(tool_calls, list):
                    for tc in tool_calls:
                        args = tc.get("args") or {}
                        if isinstance(args, dict):
                            cwd = args.get("Cwd")
                            if cwd and isinstance(cwd, str):
                                cwd_clean = cwd.strip().rstrip("`\"';,")
                                if os.path.isdir(cwd_clean):
                                    norm = normalize_workspace_uri("file://" + cwd_clean, user_home=home)
                                    if is_valid_workspace_uri(norm, user_home=home):
                                        return norm

                            for k in ("AbsolutePath", "TargetFile"):
                                fpath = args.get(k)
                                if fpath and isinstance(fpath, str):
                                    fpath_clean = unquote(urlsplit(fpath).path) if fpath.startswith("file://") else fpath
                                    fpath_clean = fpath_clean.strip().strip('"`\'')
                                    if os.path.isfile(fpath_clean) or os.path.isdir(fpath_clean):
                                        p_dir = fpath_clean if os.path.isdir(fpath_clean) else os.path.dirname(fpath_clean)
                                        if os.path.isdir(p_dir):
                                            norm = normalize_workspace_uri("file://" + p_dir, user_home=home)
                                            if is_valid_workspace_uri(norm, user_home=home):
                                                return norm
    except Exception:
        pass

    return None


def synthesize_db_from_transcript(
    conv_id: str,
    db_path: Union[str, Path],
    transcript_path: Union[str, Path],
    workspace_uri: Optional[str] = None,
    project_id: Optional[str] = None,
) -> bool:
    """
    Synthesizes a valid SQLite conversation database from transcript JSON lines with full Protobuf payloads.
    Prefers transcript_full.jsonl if available to avoid truncated messages.
    """
    tf_str = str(transcript_path)
    if tf_str.endswith("transcript.jsonl"):
        full_tf = tf_str.replace("transcript.jsonl", "transcript_full.jsonl")
        if os.path.isfile(full_tf):
            tf_str = full_tf

    if not os.path.isfile(tf_str):
        return False

    db_str = str(db_path)
    try:
        os.makedirs(os.path.dirname(db_str), exist_ok=True)
        conn = sqlite3.connect(db_str, timeout=15.0)
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS `trajectory_meta` (
            `trajectory_id` text, `cascade_id` text, `trajectory_type` integer, `source` integer, PRIMARY KEY (`trajectory_id`)
        );""")
        cur.execute("""CREATE TABLE IF NOT EXISTS `steps` (
            `idx` integer, `step_type` integer NOT NULL DEFAULT 0, `status` integer NOT NULL DEFAULT 0,
            `has_subtrajectory` numeric NOT NULL DEFAULT false, `metadata` blob, `error_details` blob,
            `permissions` blob, `task_details` blob, `render_info` blob, `step_payload` blob,
            `step_format` integer NOT NULL DEFAULT 0, PRIMARY KEY (`idx`)
        );""")
        cur.execute("""CREATE TABLE IF NOT EXISTS `gen_metadata` (`idx` integer, `data` blob, `size` integer NOT NULL DEFAULT 0, PRIMARY KEY (`idx`));""")
        cur.execute("""CREATE TABLE IF NOT EXISTS `executor_metadata` (`idx` integer, `data` blob, PRIMARY KEY (`idx`));""")
        cur.execute("""CREATE TABLE IF NOT EXISTS `parent_references` (`idx` integer, `data` blob, PRIMARY KEY (`idx`));""")
        cur.execute("""CREATE TABLE IF NOT EXISTS `trajectory_metadata_blob` (`id` text DEFAULT "main", `data` blob, PRIMARY KEY (`id`));""")
        cur.execute("""CREATE TABLE IF NOT EXISTS `battle_mode_infos` (`idx` integer, `data` blob, PRIMARY KEY (`idx`));""")

        # Extract workspace if not provided
        if not workspace_uri:
            workspace_uri = extract_workspace_from_transcript(tf_str, project_id=project_id, user_home=get_user_home())

        ws_blob = build_trajectory_metadata_blob(conv_id, workspace_uri, project_id)
        cur.execute("INSERT OR REPLACE INTO trajectory_meta VALUES (?, ?, 4, 1);", (conv_id, conv_id))
        cur.execute("INSERT OR REPLACE INTO trajectory_metadata_blob VALUES (\"main\", ?);", (ws_blob,))

        tool_types = {
            "VIEW_FILE", "RUN_COMMAND", "GENERIC", "GREP_SEARCH", "LIST_DIRECTORY",
            "SEARCH_WEB", "READ_URL_CONTENT", "GENERATE_IMAGE", "ASK_QUESTION",
            "CODE_ACTION", "ERROR_MESSAGE", "WRITE_TO_FILE", "REPLACE_FILE_CONTENT",
            "MULTI_REPLACE_FILE_CONTENT", "EDIT_FILE", "FIND_BY_NAME", "BROWSER_SUBAGENT",
            "BROWSER_ACTION", "SCHEDULE", "INVOKE_SUBAGENT", "MANAGE_SUBAGENTS",
            "MANAGE_TASK", "SEND_MESSAGE",
        }

        pending_tool_calls: List[Dict[str, Any]] = []
        steps_rows: List[Tuple[int, int, int, bytes, bytes]] = []
        out_idx = 0
        with open(tf_str, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                src = str(entry.get("source", "")).upper()
                typ = str(entry.get("type", "")).upper()
                st_str = str(entry.get("status", "DONE")).upper()
                content = entry.get("content", "")
                thinking = entry.get("thinking", "")
                tool_calls = entry.get("tool_calls", [])

                # Skip internal transcript-only system markers
                if typ in ["CHECKPOINT", "CONVERSATION_HISTORY", "KNOWLEDGE_ARTIFACTS", "EPHEMERAL_MESSAGE", "SYSTEM_MESSAGE"] or src == "SYSTEM":
                    continue

                is_tool = (
                    typ in tool_types
                    or bool(entry.get("tool_action") or entry.get("tool_summary"))
                    or src in ["TOOL", "SYSTEM_TOOL"]
                )

                # Classify step
                if is_tool:
                    step_type = 132
                elif typ == "USER_INPUT" or (src == "USER_EXPLICIT" and not is_tool) or (
                    src not in ["MODEL", "TOOL", "ASSISTANT"] and isinstance(content, str) and "<USER_REQUEST>" in content
                ):
                    step_type = 14
                    pending_tool_calls.clear()
                elif typ == "PLANNER_RESPONSE" or src == "MODEL" or thinking or tool_calls:
                    step_type = 15
                    if tool_calls:
                        pending_tool_calls.clear()
                else:
                    if content:
                        step_type = 15 if src == "MODEL" else 14
                        if step_type == 14:
                            pending_tool_calls.clear()
                    else:
                        continue

                status = 4 if st_str == "ERROR" else 3

                # Step metadata blob
                meta = bytearray()
                meta += encode_tag_bytes(12, conv_id.encode("utf-8"))
                sub_meta = bytearray()
                sub_meta += encode_tag_bytes(1, conv_id.encode("utf-8"))
                sub_meta += encode_tag_bytes(4, conv_id.encode("utf-8"))
                meta += encode_tag_bytes(20, bytes(sub_meta))

                payload = bytearray()
                payload += encode_tag_uint(1, step_type)
                payload += encode_tag_uint(4, status)

                if step_type == 14:
                    payload += encode_tag_bytes(5, bytes(meta))
                    clean = content
                    if isinstance(content, str):
                        m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                        clean = m.group(1).strip() if m else content.strip()
                    else:
                        clean = str(content)
                    u_bytes = bytearray()
                    if clean:
                        u_bytes += encode_tag_bytes(2, clean.encode("utf-8", errors="ignore"))
                        chunk = bytearray()
                        chunk += encode_tag_bytes(1, clean.encode("utf-8", errors="ignore"))
                        u_bytes += encode_tag_bytes(3, bytes(chunk))
                    payload += encode_tag_bytes(19, bytes(u_bytes))

                elif step_type == 15:
                    payload += encode_tag_bytes(5, bytes(meta))
                    m_bytes = bytearray()
                    if content:
                        m_bytes += encode_tag_bytes(1, str(content).encode("utf-8", errors="ignore"))
                    if thinking:
                        m_bytes += encode_tag_bytes(3, str(thinking).encode("utf-8", errors="ignore"))
                    m_bytes += encode_tag_bytes(6, b"antigravity-agent")
                    if tool_calls:
                        for tci, tc in enumerate(tool_calls):
                            pending_tool_calls.append(tc)
                            tc_b = bytearray()
                            tc_id = tc.get("id") or f"call_{out_idx}_{tci}"
                            tc_name = tc.get("name") or tc.get("function", {}).get("name", "")
                            tc_args = tc.get("args") or tc.get("function", {}).get("arguments", "")
                            if isinstance(tc_args, (dict, list)):
                                tc_args_str = json.dumps(tc_args)
                            else:
                                tc_args_str = str(tc_args)
                            if tc_id:
                                tc_b += encode_tag_bytes(1, str(tc_id).encode("utf-8", errors="ignore"))
                            if tc_name:
                                tc_b += encode_tag_bytes(2, str(tc_name).encode("utf-8", errors="ignore"))
                            if tc_args_str:
                                tc_b += encode_tag_bytes(3, str(tc_args_str).encode("utf-8", errors="ignore"))
                            if tc_name:
                                tc_b += encode_tag_bytes(9, str(tc_name).encode("utf-8", errors="ignore"))
                            m_bytes += encode_tag_bytes(7, bytes(tc_b))
                    if content:
                        m_bytes += encode_tag_bytes(8, str(content).encode("utf-8", errors="ignore"))
                    m_bytes += encode_tag_uint(12, 2)
                    payload += encode_tag_bytes(20, bytes(m_bytes))

                elif step_type == 132:
                    tc = pending_tool_calls.pop(0) if pending_tool_calls else {}
                    tc_id = tc.get("id") or f"call_{out_idx}"
                    tc_name = tc.get("name") or typ.lower()
                    tc_args = tc.get("args", {})
                    if isinstance(tc_args, str):
                        try:
                            tc_args = json.loads(tc_args)
                        except Exception:
                            tc_args = {}

                    tc_b = bytearray()
                    tc_b += encode_tag_bytes(1, str(tc_id).encode("utf-8", errors="ignore"))
                    tc_b += encode_tag_bytes(2, str(tc_name).encode("utf-8", errors="ignore"))
                    tc_b += encode_tag_bytes(3, json.dumps(tc_args).encode("utf-8", errors="ignore"))
                    tc_b += encode_tag_bytes(9, str(tc_name).encode("utf-8", errors="ignore"))
                    meta += encode_tag_bytes(4, bytes(tc_b))

                    payload += encode_tag_bytes(5, bytes(meta))

                    t_bytes = bytearray()
                    if isinstance(tc_args, dict):
                        for k, v in tc_args.items():
                            pair = bytearray()
                            pair += encode_tag_bytes(1, str(k).encode("utf-8", errors="ignore"))
                            val_str = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                            pair += encode_tag_bytes(2, val_str.encode("utf-8", errors="ignore"))
                            t_bytes += encode_tag_bytes(1, bytes(pair))
                    if content:
                        out_sub = bytearray()
                        out_sub += encode_tag_bytes(1, str(content).encode("utf-8", errors="ignore"))
                        t_bytes += encode_tag_bytes(2, bytes(out_sub))
                    payload += encode_tag_bytes(140, bytes(t_bytes))

                steps_rows.append((out_idx, step_type, status, bytes(meta), bytes(payload)))
                out_idx += 1

        if steps_rows:
            cur.execute("DELETE FROM steps;")
            cur.executemany(
                """INSERT OR REPLACE INTO steps 
                (idx, step_type, status, metadata, step_payload) VALUES (?, ?, ?, ?, ?);""",
                steps_rows,
            )
            conn.commit()
            return True
        else:
            return False
    except Exception:
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def repair_database_step_gaps(
    db_path: Union[str, Path],
    transcript_path: Union[str, Path],
) -> int:
    """
    Detects and repairs missing step index gaps in a conversation SQLite database
    by synthesizing only the missing steps from transcript.jsonl.
    Preserves all existing authentic steps, metadata, and binary blobs.
    Returns:
        Number of missing steps successfully backfilled.
    """
    db_p = str(db_path)
    tf_str = str(transcript_path)
    if not os.path.isfile(db_p) or not os.path.isfile(tf_str):
        return 0

    if tf_str.endswith("transcript.jsonl"):
        full_tf = tf_str.replace("transcript.jsonl", "transcript_full.jsonl")
        if os.path.isfile(full_tf):
            tf_str = full_tf

    conn = None
    try:
        conn = sqlite3.connect(db_p, timeout=15.0)
        cur = conn.cursor()
        cur.execute("SELECT idx FROM steps;")
        existing_indices = set(r[0] for r in cur.fetchall())
        if not existing_indices:
            return 0
        max_idx = max(existing_indices)
        missing_indices = set(range(max_idx + 1)) - existing_indices
        if not missing_indices:
            return 0

        conv_id = Path(db_p).stem
        tool_types = {
            "VIEW_FILE", "RUN_COMMAND", "GENERIC", "GREP_SEARCH", "LIST_DIRECTORY",
            "SEARCH_WEB", "READ_URL_CONTENT", "GENERATE_IMAGE", "ASK_QUESTION",
            "CODE_ACTION", "ERROR_MESSAGE", "WRITE_TO_FILE", "REPLACE_FILE_CONTENT",
            "MULTI_REPLACE_FILE_CONTENT", "EDIT_FILE", "FIND_BY_NAME", "BROWSER_SUBAGENT",
            "BROWSER_ACTION", "SCHEDULE", "INVOKE_SUBAGENT", "MANAGE_SUBAGENTS",
            "MANAGE_TASK", "SEND_MESSAGE",
        }

        rows_to_insert = []
        with open(tf_str, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                step_idx = entry.get("step_index")
                if step_idx is None or step_idx not in missing_indices:
                    continue

                src = str(entry.get("source", "")).upper()
                typ = str(entry.get("type", "")).upper()
                st_str = str(entry.get("status", "DONE")).upper()
                content = entry.get("content", "")
                thinking = entry.get("thinking", "")
                tool_calls = entry.get("tool_calls", [])

                is_tool = (
                    typ in tool_types
                    or bool(entry.get("tool_action") or entry.get("tool_summary"))
                    or src in ["TOOL", "SYSTEM_TOOL"]
                )

                if is_tool:
                    step_type = 132
                elif typ == "USER_INPUT" or (src == "USER_EXPLICIT" and not is_tool) or (
                    src not in ["MODEL", "TOOL", "ASSISTANT"] and isinstance(content, str) and "<USER_REQUEST>" in content
                ):
                    step_type = 14
                elif typ == "PLANNER_RESPONSE" or src == "MODEL" or thinking or tool_calls:
                    step_type = 15
                else:
                    step_type = 15 if src == "MODEL" else 14

                status = 4 if st_str == "ERROR" else 3

                meta = bytearray()
                meta += encode_tag_bytes(12, conv_id.encode("utf-8"))
                sub_meta = bytearray()
                sub_meta += encode_tag_bytes(1, conv_id.encode("utf-8"))
                sub_meta += encode_tag_bytes(4, conv_id.encode("utf-8"))
                meta += encode_tag_bytes(20, bytes(sub_meta))

                payload = bytearray()
                payload += encode_tag_uint(1, step_type)
                payload += encode_tag_uint(4, status)

                if step_type == 14:
                    payload += encode_tag_bytes(5, bytes(meta))
                    clean = content
                    if isinstance(content, str):
                        m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                        clean = m.group(1).strip() if m else content.strip()
                    else:
                        clean = str(content)
                    u_bytes = bytearray()
                    if clean:
                        u_bytes += encode_tag_bytes(2, clean.encode("utf-8", errors="ignore"))
                        chunk = bytearray()
                        chunk += encode_tag_bytes(1, clean.encode("utf-8", errors="ignore"))
                        u_bytes += encode_tag_bytes(3, bytes(chunk))
                    payload += encode_tag_bytes(19, bytes(u_bytes))

                elif step_type == 15:
                    payload += encode_tag_bytes(5, bytes(meta))
                    m_bytes = bytearray()
                    if content:
                        m_bytes += encode_tag_bytes(1, str(content).encode("utf-8", errors="ignore"))
                    if thinking:
                        m_bytes += encode_tag_bytes(3, str(thinking).encode("utf-8", errors="ignore"))
                    m_bytes += encode_tag_bytes(6, b"antigravity-agent")
                    if content:
                        m_bytes += encode_tag_bytes(8, str(content).encode("utf-8", errors="ignore"))
                    m_bytes += encode_tag_uint(12, 2)
                    payload += encode_tag_bytes(20, bytes(m_bytes))

                elif step_type == 132:
                    tc_b = bytearray()
                    tc_name = typ.lower()
                    tc_b += encode_tag_bytes(1, f"call_{step_idx}".encode("utf-8"))
                    tc_b += encode_tag_bytes(2, tc_name.encode("utf-8"))
                    tc_b += encode_tag_bytes(9, tc_name.encode("utf-8"))
                    meta += encode_tag_bytes(4, bytes(tc_b))

                    payload += encode_tag_bytes(5, bytes(meta))
                    t_bytes = bytearray()
                    if content:
                        out_sub = bytearray()
                        out_sub += encode_tag_bytes(1, str(content).encode("utf-8", errors="ignore"))
                        t_bytes += encode_tag_bytes(2, bytes(out_sub))
                    payload += encode_tag_bytes(140, bytes(t_bytes))

                rows_to_insert.append((step_idx, step_type, status, bytes(meta), bytes(payload)))

        if rows_to_insert:
            cur.executemany(
                "INSERT OR IGNORE INTO steps (idx, step_type, status, metadata, step_payload) VALUES (?, ?, ?, ?, ?);",
                rows_to_insert,
            )
            conn.commit()
            return len(rows_to_insert)
        return 0
    except Exception:
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

