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
from typing import Any, Dict, List, Optional, Union

from antigravity_suite.config import DEFAULT_CONFIG, get_user_home
from antigravity_suite.proto.trajectory import build_trajectory_metadata_blob
from antigravity_suite.proto.wire import encode_tag_bytes, encode_tag_uint, read_varint


def is_synthesized_db_incomplete(db_path: Union[str, Path]) -> bool:
    """
    Checks if a conversation SQLite database has missing/empty message payloads
    (e.g. legacy synthesized databases missing Tag 20 assistant messages or Step 132 tool metadata).
    STRICTLY protects authentic databases containing rich step types from ever being re-synthesized.
    """
    db_p = str(db_path)
    if not os.path.isfile(db_p) or os.path.getsize(db_p) == 0:
        return True
    try:
        conn = sqlite3.connect(db_p, timeout=15.0)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM steps;")
        total_steps = cur.fetchone()[0]
        if total_steps == 0:
            conn.close()
            return True

        # Check step types: if authentic rich step types exist, protect completely!
        cur.execute("SELECT DISTINCT step_type FROM steps;")
        step_types = {r[0] for r in cur.fetchall()}
        rich_authentic_types = step_types - {0, 14, 15, 132}
        if rich_authentic_types:
            conn.close()
            return False

        # For synthesized databases (only 14, 15, 132), check if assistant text is present
        cur.execute("SELECT step_payload FROM steps WHERE step_type = 15 LIMIT 5;")
        s15_rows = cur.fetchall()
        if s15_rows:
            # Wire format for tag 20 wire type 2: (20 << 3) | 2 = 162 = 0xa2, 0x01
            has_tag20 = any(row[0] and b"\xa2\x01" in row[0] for row in s15_rows)
            if not has_tag20:
                conn.close()
                return True

        # Check step 132: verify tool execution metadata is present
        cur.execute("SELECT metadata, step_payload FROM steps WHERE step_type = 132 LIMIT 5;")
        s132_rows = cur.fetchall()
        if s132_rows:
            # Tag 4 in metadata: (4 << 3) | 2 = 0x22
            has_tool_meta = any(row[0] and len(row[0]) > 20 and b"\x22" in row[0] for row in s132_rows)
            # Tag 140 in payload: (140 << 3) | 2 = 1122 = 0xe2, 0x08
            has_tool_payload = any(row[1] and b"\xe2\x08" in row[1] for row in s132_rows)
            if not (has_tool_meta and has_tool_payload):
                conn.close()
                return True

        conn.close()
        return False
    except Exception:
        return True


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
                                if (tw_c & 7) == 2:
                                    lc, p_chunk = read_varint(v19, p_chunk)
                                    vc = v19[p_chunk : p_chunk + lc]
                                    p_chunk += lc
                                    if (tw_c >> 3) == 1:
                                        try:
                                            chunk_text = vc.decode("utf-8", errors="ignore")
                                        except Exception:
                                            pass
                                elif (tw_c & 7) == 0:
                                    _, p_chunk = read_varint(v19, p_chunk)
                                else:
                                    break
                    elif w19 == 0:
                        _, p19 = read_varint(val, p19)
                    else:
                        break
        elif wire_type == 0:
            _, pos = read_varint(payload, pos)
        else:
            break

    raw_res = clean_text or chunk_text
    m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", raw_res, re.DOTALL)
    if m:
        return m.group(1).strip()
    return raw_res.strip()


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
            user_home = str(get_user_home())
            with open(tf_str, "r", encoding="utf-8", errors="ignore") as tf_f:
                for line in tf_f:
                    if "Active Document:" in line:
                        m = re.search(r"Active Document:\s*([^\s\n\r]+)", line)
                        if m:
                            doc_p = m.group(1).strip()
                            workspace_uri = "file://" + os.path.dirname(doc_p)
                            break
                    elif "Active Workspaces:" in line or "Workspace" in line:
                        m = re.search(r"file:///[^\s\n\r\"'>]+", line)
                        if m:
                            workspace_uri = m.group(0).strip()
                            break
                    elif "file:///" in line:
                        m = re.search(r"file://(/[^/][^\s\n\r\"'>]+)", line)
                        if m:
                            p_cand = m.group(1).rstrip(",.;'\"")
                            if os.path.isdir(p_cand):
                                workspace_uri = "file://" + p_cand
                                break
                            elif os.path.isfile(p_cand) or "/" in p_cand:
                                workspace_uri = "file://" + os.path.dirname(p_cand)
                                break

        ws_blob = build_trajectory_metadata_blob(conv_id, workspace_uri, project_id)
        cur.execute("INSERT OR REPLACE INTO trajectory_meta VALUES (?, ?, 4, 1);", (conv_id, conv_id))
        cur.execute("INSERT OR REPLACE INTO trajectory_metadata_blob VALUES (\"main\", ?);", (ws_blob,))

        # Clear existing steps table in case of re-synthesis
        cur.execute("DELETE FROM steps;")

        pending_tool_calls: List[Dict[str, Any]] = []
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
                src = entry.get("source", "")
                typ = entry.get("type", "")
                st_str = entry.get("status", "DONE")
                content = entry.get("content", "")
                thinking = entry.get("thinking", "")
                tool_calls = entry.get("tool_calls", [])

                # Skip internal transcript-only system markers
                if typ in ["CHECKPOINT", "CONVERSATION_HISTORY", "KNOWLEDGE_ARTIFACTS", "EPHEMERAL_MESSAGE", "SYSTEM_MESSAGE"] or src == "SYSTEM":
                    continue

                # Classify step
                if typ == "USER_INPUT" or ("<USER_REQUEST>" in content and src != "MODEL") or (src == "USER_EXPLICIT" and typ not in ["VIEW_FILE", "CODE_ACTION"]):
                    step_type = 14
                elif typ in ["VIEW_FILE", "RUN_COMMAND", "GENERIC", "GREP_SEARCH", "LIST_DIRECTORY", "SEARCH_WEB", "READ_URL_CONTENT", "GENERATE_IMAGE", "ASK_QUESTION", "CODE_ACTION", "ERROR_MESSAGE"]:
                    step_type = 132
                elif typ == "PLANNER_RESPONSE" or src == "MODEL" or thinking or tool_calls:
                    step_type = 15
                else:
                    if content:
                        step_type = 15 if src == "MODEL" else 14
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
                    m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                    if m:
                        clean = m.group(1).strip()
                    else:
                        clean = content.strip()
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
                        m_bytes += encode_tag_bytes(1, content.encode("utf-8", errors="ignore"))
                    if thinking:
                        m_bytes += encode_tag_bytes(3, thinking.encode("utf-8", errors="ignore"))
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
                        m_bytes += encode_tag_bytes(8, content.encode("utf-8", errors="ignore"))
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
                            val_str = json.dumps(v) if isinstance(v, (dict, list)) else str(v).strip("\"")
                            pair += encode_tag_bytes(2, val_str.encode("utf-8", errors="ignore"))
                            t_bytes += encode_tag_bytes(1, bytes(pair))
                    if content:
                        out_sub = bytearray()
                        out_sub += encode_tag_bytes(1, content.encode("utf-8", errors="ignore"))
                        t_bytes += encode_tag_bytes(2, bytes(out_sub))
                    payload += encode_tag_bytes(140, bytes(t_bytes))

                cur.execute("""INSERT OR REPLACE INTO steps 
                    (idx, step_type, status, metadata, step_payload) VALUES (?, ?, ?, ?, ?);""",
                    (out_idx, step_type, status, bytes(meta), bytes(payload)))
                out_idx += 1

        conn.commit()
        conn.close()
        return out_idx > 0
    except Exception:
        return False
