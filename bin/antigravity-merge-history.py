#!/usr/bin/env python3
# ==============================================================================
# Antigravity Multi-Instance History Merger & Real-Time Sync Daemon
# Bidirectionally synchronizes conversations, summaries, and layouts across:
#   - Antigravity Desktop App (Account 1 & Clones)
#   - Antigravity IDE (VS Code edition)
# Handles protobuf formats:
#   Format A (Disk LS): SummariesState (proto map: uuid -> CascadeTrajectorySummary)
#   Format B (VS Code): UnifiedStateSyncTopicData (proto map: uuid -> ValueWrapper(base64))
#   Format C (SQLite):  conversation_summaries.db (raw_summary = binary CascadeTrajectorySummary)
#   Format D (Layout):  app_storage.json (antigravity-multi-conversation-layout-v3-<uuid>)
# ==============================================================================

import os
import sys
import glob
import json
import re
import sqlite3
import shutil
import datetime
import base64
import time
import argparse
import urllib.request
import urllib.parse

def encode_varint(value):
    if value < 0:
        value &= 0xffffffffffffffff
    out = bytearray()
    while value > 0x7f:
        out.append((value & 0x7f) | 0x80)
        value >>= 7
    out.append(value & 0x7f)
    return bytes(out)

def read_varint(data, pos):
    length = 0
    shift = 0
    total = len(data)
    while pos < total:
        b = data[pos]
        pos += 1
        length |= (b & 0x7f) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    return length, pos

def encode_tag_bytes(field_num, b):
    tag = (field_num << 3) | 2
    return encode_varint(tag) + encode_varint(len(b)) + b

def encode_tag_uint(field_num, val):
    tag = (field_num << 3) | 0
    return encode_varint(tag) + encode_varint(val)

def encode_timestamp_field(field_num, ts_sec, ts_nanos=0):
    body = bytearray()
    body.extend(encode_tag_uint(1, ts_sec))
    if ts_nanos:
        body.extend(encode_tag_uint(2, ts_nanos))
    return encode_tag_bytes(field_num, body)

def encode_annotations_field(title):
    body = bytearray()
    if title:
        t_bytes = title.encode('utf-8', 'ignore')[:150]
        body.extend(encode_tag_bytes(1, t_bytes))
    return encode_tag_bytes(15, body)

def get_last_user_step_index(conv_db_path, step_count=0):
    if conv_db_path and os.path.isfile(conv_db_path):
        try:
            c = sqlite3.connect(conv_db_path)
            row = c.cursor().execute("SELECT idx FROM steps WHERE step_type = 14 ORDER BY idx DESC LIMIT 1;").fetchone()
            c.close()
            if row is not None:
                return row[0]
        except Exception:
            pass
    return max(0, step_count - 1)

def build_cascade_summary(uuid_str, title, summary_text, step_count=1, mtime_iso="", created_iso="", last_user_step=None):
    """
    Creates a complete standard binary CascadeTrajectorySummary protobuf:
      Field 1: summary (string - UI preview/summary)
      Field 2: step_count (uint32)
      Field 3: last_modified_time (Timestamp)
      Field 4: trajectory_id (string UUID)
      Field 5: status (1 = CASCADE_RUN_STATUS_IDLE)
      Field 7: created_time (Timestamp)
      Field 10: last_user_input_time (Timestamp)
      Field 15: annotations (ConversationAnnotations containing subfield 1 = title)
      Field 16: last_user_input_step_index (uint32)
      Field 20: source (17)
      Field 22: trajectory_type (4)
      Field 28: latest_executor_termination_reason (2)
    """
    out = bytearray()
    clean_title = (title or summary_text or "Conversation").strip().split('\n')[0].strip()[:100]
    out.extend(encode_tag_bytes(1, clean_title.encode('utf-8', 'ignore')))
    out.extend(encode_tag_uint(2, max(1, step_count)))

    try:
        if mtime_iso:
            if isinstance(mtime_iso, (int, float)):
                ts_sec = int(mtime_iso)
            else:
                dt = datetime.datetime.fromisoformat(str(mtime_iso).replace('Z', '+00:00'))
                ts_sec = int(dt.timestamp())
        else:
            ts_sec = int(time.time())
    except Exception:
        ts_sec = int(time.time())
    out.extend(encode_timestamp_field(3, ts_sec))

    t_bytes = uuid_str.encode('ascii')
    out.extend(encode_tag_bytes(4, t_bytes))
    out.extend(encode_tag_uint(5, 1))

    try:
        if created_iso:
            if isinstance(created_iso, (int, float)):
                c_sec = int(created_iso)
            else:
                dt = datetime.datetime.fromisoformat(str(created_iso).replace('Z', '+00:00'))
                c_sec = int(dt.timestamp())
        else:
            c_sec = ts_sec
    except Exception:
        c_sec = ts_sec
    out.extend(encode_timestamp_field(7, c_sec))
    out.extend(encode_timestamp_field(10, ts_sec))

    out.extend(encode_annotations_field(clean_title[:80]))

    if last_user_step is None or last_user_step < 0:
        actual_step = max(0, step_count - 1)
    else:
        actual_step = last_user_step
    out.extend(encode_tag_uint(16, actual_step))
    out.extend(encode_tag_uint(20, 17))
    out.extend(encode_tag_uint(22, 4))
    out.extend(encode_tag_uint(28, 2))

    return bytes(out)

def parse_cascade_summary(raw):
    """Parses pure binary CascadeTrajectorySummary and extracts known fields."""
    if not raw or not isinstance(raw, (bytes, bytearray)):
        return {}
    res = {}
    pos = 0
    total = len(raw)
    try:
        while pos < total:
            tag, pos = read_varint(raw, pos)
            wire = tag & 0x7
            fn = tag >> 3
            if wire == 0:
                val, pos = read_varint(raw, pos)
                res[fn] = val
            elif wire == 2:
                length, pos = read_varint(raw, pos)
                val = raw[pos:pos+length]
                pos += length
                if fn == 1:
                    res["summary"] = val.decode("utf-8", "ignore")
                elif fn == 3:
                    spos = 0
                    while spos < len(val):
                        stag, spos = read_varint(val, spos)
                        sfn = stag >> 3
                        swt = stag & 7
                        if swt == 0:
                            sval, spos = read_varint(val, spos)
                            if sfn == 1:
                                res["last_modified_time"] = sval
                        elif swt == 2:
                            slen, spos = read_varint(val, spos)
                            spos += slen
                        else:
                            break
                elif fn == 4:
                    res["trajectory_id"] = val.decode("ascii", "ignore")
                elif fn == 7:
                    spos = 0
                    while spos < len(val):
                        stag, spos = read_varint(val, spos)
                        sfn = stag >> 3
                        swt = stag & 7
                        if swt == 0:
                            sval, spos = read_varint(val, spos)
                            if sfn == 1:
                                res["created_time"] = sval
                        elif swt == 2:
                            slen, spos = read_varint(val, spos)
                            spos += slen
                        else:
                            break
                elif fn == 10:
                    spos = 0
                    while spos < len(val):
                        stag, spos = read_varint(val, spos)
                        sfn = stag >> 3
                        swt = stag & 7
                        if swt == 0:
                            sval, spos = read_varint(val, spos)
                            if sfn == 1:
                                res["last_user_input_time"] = sval
                        elif swt == 2:
                            slen, spos = read_varint(val, spos)
                            spos += slen
                        else:
                            break
                elif fn == 15:
                    subpos = 0
                    while subpos < len(val):
                        subtag, subpos = read_varint(val, subpos)
                        subwire = subtag & 0x7
                        subfn = subtag >> 3
                        if subwire == 2:
                            sublen, subpos = read_varint(val, subpos)
                            subdata = val[subpos:subpos+sublen]
                            subpos += sublen
                            if subfn == 1:
                                res["title"] = subdata.decode("utf-8", "ignore")
                        elif subwire == 0:
                            _, subpos = read_varint(val, subpos)
                        else:
                            break
            elif wire == 1:
                pos += 8
            elif wire == 5:
                pos += 4
            else:
                break
    except Exception:
        pass
    return res

def extract_pure_binary_summary(raw):
    """Extract pure binary CascadeTrajectorySummary from any raw blob or ValueWrapper."""
    if not raw or not isinstance(raw, (bytes, bytearray)):
        return None
    # Check if raw is wrapped in ValueWrapper: tag 0x0a + varint len + base64 string
    if raw.startswith(b'\n'):
        pos = 1
        length, pos = read_varint(raw, pos)
        if pos + length <= len(raw):
            candidate_b64 = raw[pos:pos+length]
            try:
                decoded = base64.b64decode(candidate_b64)
                if decoded and decoded.startswith(b'\n'):
                    return decoded
            except Exception:
                pass
    return bytes(raw)

def extract_entries_from_proto(data):
    """
    Parses map<string, ...> from either SummariesState (Format A)
    or UnifiedStateSyncTopicData (Format B).
    Returns dict: { uuid: pure_binary_summary_bytes }
    """
    entries = {}
    pos = 0
    total = len(data)
    while pos < total:
        tag = data[pos]
        pos += 1
        length, pos = read_varint(data, pos)
        if pos + length > total:
            break
        entry_data = data[pos:pos+length]
        pos += length
        
        # In a map entry, tag 0x0a is key (uuid string, length 36)
        if tag == 0x0a and len(entry_data) > 38 and entry_data[0] == 0x0a and entry_data[1] == 0x24:
            uuid = entry_data[2:38].decode('ascii', 'ignore')
            val_chunk = entry_data[38:]
            if len(val_chunk) > 2 and val_chunk[0] == 0x12:
                vlen, vpos = read_varint(val_chunk, 1)
                raw_val = val_chunk[vpos:vpos+vlen]
                pure = extract_pure_binary_summary(raw_val)
                if pure:
                    entries[uuid] = pure
    return entries

def get_annotation_title(master_gemini, conv_id, search_dirs=None):
    """Extracts user-defined or AI-generated title from annotations/<conv_id>.pbtxt across all roots."""
    roots = [master_gemini]
    if search_dirs:
        roots.extend(search_dirs)
    for g_dir in roots:
        anno_file = os.path.join(g_dir, "annotations", f"{conv_id}.pbtxt")
        if os.path.isfile(anno_file):
            try:
                with open(anno_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    m = re.search(r'title\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', content)
                    if m:
                        raw_str = m.group(1)
                        if r'\u' in raw_str or r'\x' in raw_str:
                            try:
                                val = raw_str.encode('latin1').decode('unicode_escape')
                            except Exception:
                                val = raw_str
                        else:
                            val = raw_str
                        clean = val.strip()
                        if clean:
                            return clean
            except Exception:
                pass
    return None

def refresh_ide_oauth_token():
    """Ensures ~/.gemini-ide/jetski-standalone-oauth-token stays refreshed for Account 2 (rezalast4m)."""
    token_file = os.path.expanduser("~/.gemini-ide/jetski-standalone-oauth-token")
    if not os.path.isfile(token_file):
        return
    try:
        with open(token_file, "r") as f:
            data = json.load(f)
        tok = data.get("token", {})
        expiry_str = tok.get("expiry")
        rt = tok.get("refresh_token")
        if not rt:
            return

        need_refresh = True
        if expiry_str:
            try:
                clean_exp = expiry_str.replace("Z", "+00:00")
                exp_dt = datetime.datetime.fromisoformat(clean_exp)
                now_dt = datetime.datetime.now(datetime.timezone.utc)
                if (exp_dt - now_dt).total_seconds() > 600:
                    need_refresh = False
            except Exception:
                need_refresh = True

        if need_refresh:
            creds_file = os.path.expanduser("~/.gemini-ide/oauth_credentials.json")
            if not os.path.isfile(creds_file):
                return
            with open(creds_file, "r") as cf:
                creds = json.load(cf)
            client_id = creds.get("client_id")
            client_secret = creds.get("client_secret")
            if not client_id or not client_secret:
                return

            body = urllib.parse.urlencode({
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": rt,
            }).encode()
            req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body)
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode())
            if "access_token" in res:
                tok["access_token"] = res["access_token"]
                exp_in = res.get("expires_in", 3599)
                new_exp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=exp_in)).isoformat()
                tok["expiry"] = new_exp
                if "id_token" in res:
                    data["id_token"] = res["id_token"]
                data["token"] = tok
                with open(token_file, "w") as f:
                    json.dump(data, f, indent=2)
                os.chmod(token_file, 0o600)

                vscdb_path = os.path.expanduser("~/.config/Antigravity IDE/User/globalStorage/state.vscdb")
                if os.path.exists(vscdb_path):
                    try:
                        v_con = sqlite3.connect(vscdb_path)
                        v_cur = v_con.cursor()
                        auth_json = json.dumps({
                            "name": "Reza Last4m",
                            "email": "rezalast4m@gmail.com",
                            "apiKey": res["access_token"]
                        })
                        v_cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityAuthStatus', ?);", (auth_json,))
                        v_con.commit()
                        v_con.close()
                    except Exception:
                        pass
    except Exception:
        pass

def parse_step14_user_prompt(payload):
    """Extracts genuine clean user request from Protobuf payload in step_type 14."""
    if not payload:
        return ""
    m = re.search(rb"<USER_REQUEST>(.*?)</USER_REQUEST>", payload, re.DOTALL)
    if m:
        try:
            return " ".join(m.group(1).decode("utf-8", "ignore").split())
        except Exception:
            pass

    pos = 0
    total = len(payload)
    while pos < total:
        tag, pos = read_varint(payload, pos)
        fn = tag >> 3
        wt = tag & 7
        if wt == 0:
            val, pos = read_varint(payload, pos)
        elif wt == 2:
            l, pos = read_varint(payload, pos)
            chunk = payload[pos:pos+l]
            pos += l
            if fn == 19:
                cpos = 0
                while cpos < len(chunk):
                    ctag, cpos = read_varint(chunk, cpos)
                    cfn = ctag >> 3
                    cwt = ctag & 7
                    if cwt == 2:
                        cl, cpos = read_varint(chunk, cpos)
                        subchunk = chunk[cpos:cpos+cl]
                        cpos += cl
                        if cfn in (2, 3):
                            try:
                                stag, spos = read_varint(subchunk, 0)
                                if (stag >> 3) == 1 and (stag & 7) == 2:
                                    sl, spos = read_varint(subchunk, spos)
                                    text = subchunk[spos:spos+sl].decode("utf-8", "ignore").strip()
                                    if text:
                                        text = re.sub(r"^@\[TerminalName:[^\]]+\]\s*", "", text)
                                        return " ".join(text.split())
                            except Exception:
                                pass
                            try:
                                text = subchunk.decode("utf-8", "ignore").strip()
                                if text:
                                    text = re.sub(r"^@\[TerminalName:[^\]]+\]\s*", "", text)
                                    return " ".join(text.split())
                            except Exception:
                                pass
                    elif cwt == 0:
                        _, cpos = read_varint(chunk, cpos)
                    else:
                        break
        else:
            break

    for match in re.finditer(rb"[\x20-\x7e\xd8-\xdb\xdc-\xdf]{8,}", payload):
        cand = match.group(0).decode("utf-8", "ignore").strip()
        if not re.match(r"^[0-9a-fA-F-]{36}", cand) and not cand.startswith("TerminalName:") and not cand.startswith("file://") and not cand.startswith("read_url(") and not cand.startswith("mcp("):
            return cand
    return ""

def is_synthesized_db_incomplete(db_path):
    """
    Checks if a conversation SQLite database has missing/empty message payloads
    (e.g. legacy synthesized databases missing Tag 20 assistant messages or Tag 19 chunk headers).
    """
    if not os.path.isfile(db_path) or os.path.getsize(db_path) == 0:
        return True
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM steps;")
        total_steps = cur.fetchone()[0]
        if total_steps == 0:
            conn.close()
            return True

        # Check step 15 (assistant messages)
        cur.execute("SELECT step_payload FROM steps WHERE step_type = 15 LIMIT 5;")
        s15_rows = cur.fetchall()
        if s15_rows:
            # Wire format for tag 20 wire type 2: (20 << 3) | 2 = 162 = 0xa2, 0x01
            has_tag20 = any(b"\xa2\x01" in row[0] for row in s15_rows if row[0])
            if not has_tag20:
                conn.close()
                return True

        # Check step 14 (user prompts)
        cur.execute("SELECT step_payload FROM steps WHERE step_type = 14 LIMIT 5;")
        s14_rows = cur.fetchall()
        if s14_rows:
            # Wire format for tag 19 subfield 3 wire type 2: (3 << 3) | 2 = 26 = 0x1a
            has_subfield3 = any(b"\x1a" in row[0] for row in s14_rows if row[0])
            if not has_subfield3:
                conn.close()
                return True

        conn.close()
        return False
    except Exception:
        return True

def synthesize_db_from_transcript(conv_id, db_path, transcript_path):
    """Synthesizes a valid SQLite conversation database from transcript JSON lines with full Protobuf payloads."""
    if not os.path.isfile(transcript_path):
        return False
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
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

        cur.execute("INSERT OR REPLACE INTO trajectory_meta VALUES (?, ?, 4, 1);", (conv_id, conv_id))
        cur.execute("INSERT OR REPLACE INTO trajectory_metadata_blob VALUES (\"main\", ?);", (conv_id.encode("utf-8"),))

        # Tracking metadata blob (Tag 5 and metadata column)
        meta = bytearray()
        meta += encode_tag_bytes(12, conv_id.encode("utf-8"))
        sub_meta = bytearray()
        sub_meta += encode_tag_bytes(1, conv_id.encode("utf-8"))
        sub_meta += encode_tag_bytes(4, conv_id.encode("utf-8"))
        meta += encode_tag_bytes(20, bytes(sub_meta))
        meta_bytes = bytes(meta)

        step_count = 0
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                idx = entry.get("step_index", step_count)
                src = entry.get("source", "")
                typ = entry.get("type", "")
                st_str = entry.get("status", "DONE")
                content = entry.get("content", "")
                thinking = entry.get("thinking", "")
                tool_calls = entry.get("tool_calls", [])

                if "<USER_REQUEST>" in content or typ == "USER_INPUT" or src == "USER_EXPLICIT":
                    step_type = 14
                elif typ in ["VIEW_FILE", "RUN_COMMAND", "GENERIC"] or (src == "MODEL" and typ == "GENERIC"):
                    step_type = 132
                elif typ == "PLANNER_RESPONSE" or src == "MODEL" or thinking or tool_calls:
                    step_type = 15
                else:
                    step_type = 1

                status = 4 if st_str == "ERROR" else 3

                payload = bytearray()
                payload += encode_tag_uint(1, step_type)
                payload += encode_tag_uint(4, status)
                payload += encode_tag_bytes(5, meta_bytes)

                if step_type == 14:
                    u_bytes = bytearray()
                    if content:
                        u_bytes += encode_tag_bytes(2, content.encode("utf-8", errors="ignore"))
                        chunk = bytearray()
                        clean = content
                        m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                        if m:
                            clean = m.group(1).strip()
                        chunk += encode_tag_bytes(1, clean.encode("utf-8", errors="ignore"))
                        u_bytes += encode_tag_bytes(3, bytes(chunk))
                    payload += encode_tag_bytes(19, bytes(u_bytes))

                elif step_type == 15:
                    m_bytes = bytearray()
                    if content:
                        m_bytes += encode_tag_bytes(1, content.encode("utf-8", errors="ignore"))
                    if thinking:
                        m_bytes += encode_tag_bytes(3, thinking.encode("utf-8", errors="ignore"))
                    m_bytes += encode_tag_bytes(6, b"antigravity-agent")
                    if tool_calls:
                        for tci, tc in enumerate(tool_calls):
                            tc_b = bytearray()
                            tc_id = tc.get("id") or f"call_{idx}_{tci}"
                            tc_name = tc.get("name") or tc.get("function", {}).get("name", "")
                            tc_args = tc.get("args") or tc.get("function", {}).get("arguments", "")
                            if isinstance(tc_args, (dict, list)):
                                tc_args = json.dumps(tc_args)
                            if tc_id:
                                tc_b += encode_tag_bytes(1, str(tc_id).encode("utf-8", errors="ignore"))
                            if tc_name:
                                tc_b += encode_tag_bytes(2, str(tc_name).encode("utf-8", errors="ignore"))
                            if tc_args:
                                tc_b += encode_tag_bytes(3, str(tc_args).encode("utf-8", errors="ignore"))
                            if tc_name:
                                tc_b += encode_tag_bytes(9, str(tc_name).encode("utf-8", errors="ignore"))
                            m_bytes += encode_tag_bytes(7, bytes(tc_b))
                    if content:
                        m_bytes += encode_tag_bytes(8, content.encode("utf-8", errors="ignore"))
                    m_bytes += encode_tag_uint(12, 2)
                    payload += encode_tag_bytes(20, bytes(m_bytes))

                elif step_type == 132:
                    t_bytes = bytearray()
                    if content:
                        t_bytes += encode_tag_bytes(2, content.encode("utf-8", errors="ignore"))
                    payload += encode_tag_bytes(140, bytes(t_bytes))

                else:
                    if content:
                        s_bytes = bytearray()
                        s_bytes += encode_tag_bytes(2, content.encode("utf-8", errors="ignore"))
                        payload += encode_tag_bytes(19, bytes(s_bytes))

                cur.execute("""INSERT OR REPLACE INTO steps 
                    (idx, step_type, status, metadata, step_payload) VALUES (?, ?, ?, ?, ?);""",
                    (idx, step_type, status, meta_bytes, bytes(payload)))
                step_count += 1

        conn.commit()
        conn.close()
        return step_count > 0
    except Exception:
        return False

def extract_conv_text(db_path, transcript_path):
    """Extracts (title, preview) from transcript, artifacts, and sqlite steps."""
    first_user_prompt = ""
    latest_user_prompt = ""

    t_candidates = []
    if transcript_path:
        t_candidates.append(transcript_path)
        if "transcript.jsonl" in transcript_path:
            t_candidates.insert(0, transcript_path.replace("transcript.jsonl", "transcript_full.jsonl"))

    for tf in t_candidates:
        if os.path.isfile(tf):
            try:
                with open(tf, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except Exception:
                            continue
                        content = data.get("content", "")
                        step_type = data.get("type", "")
                        source = data.get("source", "")
                        if content and ("<USER_REQUEST>" in content or step_type == "USER_INPUT" or source == "USER_EXPLICIT"):
                            m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                            req = m.group(1).strip() if m else content.strip()
                            clean = " ".join(req.split())
                            if not first_user_prompt:
                                first_user_prompt = clean
                            latest_user_prompt = clean
                if first_user_prompt:
                    break
            except Exception:
                pass

    if os.path.isfile(db_path):
        try:
            c = sqlite3.connect(db_path)
            cur = c.cursor()
            rows = cur.execute("SELECT idx, step_payload FROM steps WHERE step_type = 14 ORDER BY idx ASC;").fetchall()
            c.close()
            for r_idx, payload in rows:
                if not payload:
                    continue
                p_text = parse_step14_user_prompt(payload)
                if p_text:
                    if not first_user_prompt:
                        first_user_prompt = p_text
                    latest_user_prompt = p_text
        except Exception:
            pass

    # Check for artifact plan/walkthrough markdown files in brain folder
    artifact_title = ""
    brain_dir = os.path.dirname(os.path.dirname(os.path.dirname(transcript_path))) if "logs" in transcript_path else ""
    if brain_dir and os.path.isdir(brain_dir):
        for f in os.listdir(brain_dir):
            if f.endswith(".md") and not f.startswith("."):
                # Try extracting genuine H1 heading (# Document Title)
                try:
                    with open(os.path.join(brain_dir, f), "r", encoding="utf-8", errors="ignore") as mf:
                        for mline in mf:
                            mline = mline.strip()
                            if mline.startswith("# ") and len(mline) > 2:
                                h1 = mline[2:].strip().strip("#").strip()
                                if h1 and h1.lower() not in ["walkthrough", "implementation plan", "task", "todo", "readme"]:
                                    artifact_title = h1
                                    break
                except Exception:
                    pass
                if artifact_title:
                    break

                name = f[:-3].replace("_", " ").replace("-", " ").strip()
                if name.lower() not in ["walkthrough", "implementation plan", "task", "todo", "readme"]:
                    artifact_title = name.title()
                    break
                elif not artifact_title:
                    artifact_title = name.title()

    title = ""
    if artifact_title and (not first_user_prompt or len(first_user_prompt) > 80 or not first_user_prompt.isascii()):
        title = artifact_title
    elif first_user_prompt:
        title = first_user_prompt[:80]
    elif artifact_title:
        title = artifact_title

    preview = latest_user_prompt[:250] if latest_user_prompt else (first_user_prompt[:250] if first_user_prompt else title)
    return title, preview

def build_summaries_state(entries_dict):
    """Builds Format A: SummariesState binary protobuf for Go language_server on disk."""
    out = bytearray()
    for uuid, pure_bin in sorted(entries_dict.items()):
        entry = bytearray()
        u_bytes = uuid.encode('ascii')
        entry.append(0x0a)
        entry.extend(encode_varint(len(u_bytes)))
        entry.extend(u_bytes)
        entry.append(0x12)
        entry.extend(encode_varint(len(pure_bin)))
        entry.extend(pure_bin)
        out.append(0x0a)
        out.extend(encode_varint(len(entry)))
        out.extend(entry)
    return bytes(out)

def build_unified_state_sync(entries_dict):
    """Builds Format B: UnifiedStateSyncTopicData binary protobuf for VS Code state.vscdb."""
    out = bytearray()
    for uuid, pure_bin in sorted(entries_dict.items()):
        b64_val = base64.b64encode(pure_bin).decode('ascii')
        b64_bytes = b64_val.encode('ascii')
        vw = bytearray()
        vw.append(0x0a)
        vw.extend(encode_varint(len(b64_bytes)))
        vw.extend(b64_bytes)
        entry = bytearray()
        u_bytes = uuid.encode('ascii')
        entry.append(0x0a)
        entry.extend(encode_varint(len(u_bytes)))
        entry.extend(u_bytes)
        entry.append(0x12)
        entry.extend(encode_varint(len(vw)))
        entry.extend(vw)
        out.append(0x0a)
        out.extend(encode_varint(len(entry)))
        out.extend(entry)
    return bytes(out)

def discover_all_history_sources(real_home, custom_sources=None):
    """
    Thoroughly discovers all conversation databases, brain directories, and custom
    installation paths across the system, including manual installations, older backups,
    standalone IDE stores, desktop launchers, and user profiles.
    """
    conv_dirs = set()
    brain_dirs = set()

    # 1. Custom sources passed via CLI / caller
    if custom_sources:
        for s in custom_sources:
            if s and os.path.exists(s):
                real_s = os.path.realpath(s)
                if os.path.isdir(s):
                    if glob.glob(os.path.join(s, "*.db")):
                        conv_dirs.add(real_s)
                    if "conversations" in os.path.basename(s):
                        conv_dirs.add(real_s)
                    if "brain" in os.path.basename(s):
                        brain_dirs.add(real_s)

    # 2. Collect all candidate user home directories
    homes = set()
    if real_home:
        homes.add(real_home)
    homes.add(os.path.expanduser("~"))
    try:
        user = os.environ.get("USER") or getpass.getuser()
        homes.add(os.path.expanduser(f"~{user}"))
    except Exception:
        pass

    # 3. Standard and named profile roots across all homes
    search_roots = set()
    for h in homes:
        if not os.path.isdir(h):
            continue
        search_roots.add(os.path.join(h, ".gemini"))
        search_roots.add(os.path.join(h, ".gemini-ide"))
        search_roots.add(os.path.join(h, ".gemide"))
        search_roots.add(os.path.join(h, ".config", "Antigravity"))
        search_roots.add(os.path.join(h, ".config", "Antigravity IDE"))
        search_roots.add(os.path.join(h, ".config", "antigravity"))
        search_roots.add(os.path.join(h, ".config", "antigravity-ide"))
        search_roots.add(os.path.join(h, ".config", "Google", "Antigravity"))
        search_roots.add(os.path.join(h, ".local", "share", "antigravity"))
        search_roots.add(os.path.join(h, ".local", "share", "Antigravity"))
        search_roots.add(os.path.join(h, ".local", "share", "Trash"))
        for p in glob.glob(os.path.join(h, ".antigravity*")):
            search_roots.add(p)
        for p in glob.glob(os.path.join(h, ".gemini*")):
            search_roots.add(p)

    # 4. Inspect desktop launchers for custom data directories
    desktop_locations = [
        "/usr/share/applications",
        "/usr/local/share/applications"
    ]
    for h in homes:
        desktop_locations.append(os.path.join(h, ".local", "share", "applications"))

    for d_dir in desktop_locations:
        if os.path.isdir(d_dir):
            for d_file in glob.glob(os.path.join(d_dir, "*.desktop")):
                try:
                    with open(d_file, "r", errors="ignore") as f:
                        content = f.read()
                        if "antigravity" in content.lower() or "gemini" in content.lower():
                            for m in re.finditer(r"--user-data-dir=[\"\']?([^\s\"\']+)[\"\']?", content):
                                search_roots.add(os.path.expanduser(m.group(1)))
                            for m in re.finditer(r"--profile-directory=[\"\']?([^\s\"\']+)[\"\']?", content):
                                search_roots.add(os.path.expanduser(m.group(1)))
                            for m in re.finditer(r"GEMINI_DIR=[\"\']?([^\s\"\']+)[\"\']?", content):
                                search_roots.add(os.path.expanduser(m.group(1)))
                except Exception:
                    pass

    # 5. Targeted recursive scan across all discovered roots (depth limited to 5)
    deep_walk_targets = set()
    for h in homes:
        if not os.path.isdir(h):
            continue
        for pat in glob.glob(os.path.join(h, ".gemini*")):
            deep_walk_targets.add(pat)
        for pat in glob.glob(os.path.join(h, ".antigravity*")):
            deep_walk_targets.add(pat)
        for pat in glob.glob(os.path.join(h, ".config", "*antigravity*")):
            deep_walk_targets.add(pat)
        for pat in glob.glob(os.path.join(h, ".config", "*Antigravity*")):
            deep_walk_targets.add(pat)
        for pat in glob.glob(os.path.join(h, ".local", "share", "*antigravity*")):
            deep_walk_targets.add(pat)
        for pat in glob.glob(os.path.join(h, ".local", "share", "*Antigravity*")):
            deep_walk_targets.add(pat)

    for droot in sorted(deep_walk_targets):
        if not os.path.isdir(droot):
            continue
        try:
            for root, dirs, files in os.walk(droot, followlinks=False):
                rel = os.path.relpath(root, droot)
                if rel.count(os.sep) > 5:
                    continue

                # Heuristic 1: Brain store detection via transcript logs
                if "transcript.jsonl" in files or "transcript_full.jsonl" in files:
                    parts = root.split(os.sep)
                    for i in range(len(parts) - 1, -1, -1):
                        if re.match(r'^[0-9a-fA-F-]{36}$', parts[i]):
                            brain_parent = os.sep.join(parts[:i])
                            if os.path.isdir(brain_parent):
                                brain_dirs.add(os.path.realpath(brain_parent))
                            break

                # Heuristic 2: Conversation database store detection via UUID .db files
                has_conv_db = any(re.match(r'^[0-9a-fA-F-]{36}\.db$', f) for f in files)
                if has_conv_db:
                    conv_dirs.add(os.path.realpath(root))

                # Heuristic 3: Directory named conversations or brain
                bname = os.path.basename(root).lower()
                if "conversations" in bname and (has_conv_db or not files):
                    conv_dirs.add(os.path.realpath(root))
                elif "brain" in bname:
                    brain_dirs.add(os.path.realpath(root))
        except Exception:
            pass

    # 6. Legacy backup history directories
    for h in homes:
        hist_backup_dir = os.path.join(h, ".config", "antigravity", "backups", "history")
        if os.path.isdir(hist_backup_dir):
            for b_cand in glob.glob(os.path.join(hist_backup_dir, "*", "conversations*")):
                if os.path.isdir(b_cand):
                    conv_dirs.add(os.path.realpath(b_cand))
            for b_cand in glob.glob(os.path.join(hist_backup_dir, "*", "brain*")):
                if os.path.isdir(b_cand):
                    brain_dirs.add(os.path.realpath(b_cand))

    return sorted(conv_dirs), sorted(brain_dirs)

def merge_histories(master_gemini=None, source_dir=None, target_dir=None, quiet=False, force_rebuild=False):
    real_home = os.environ.get("REAL_HOME", os.path.expanduser("~"))
    homes = set()
    if real_home:
        homes.add(real_home)
    homes.add(os.path.expanduser("~"))
    try:
        user = os.environ.get("USER") or getpass.getuser()
        homes.add(os.path.expanduser(f"~{user}"))
    except Exception:
        pass

    if not master_gemini:
        if target_dir:
            master_gemini = os.path.dirname(target_dir) if target_dir.rstrip("/").endswith("conversations") else target_dir
        else:
            master_gemini = os.path.join(real_home, ".gemini", "antigravity")

    master_conv_dir = os.path.join(master_gemini, "conversations")
    master_brain_dir = os.path.join(master_gemini, "brain")
    master_sum_db = os.path.join(master_gemini, "conversation_summaries.db")

    os.makedirs(master_conv_dir, exist_ok=True)
    os.makedirs(master_brain_dir, exist_ok=True)

    # 1. Discover all history pools across the system
    custom_srcs = [source_dir] if source_dir else None
    candidate_conv_dirs, candidate_brain_dirs = discover_all_history_sources(real_home, custom_srcs)

    # 2. Copy missing .db files and brain directories into master
    copied_dbs = 0
    copied_brains = 0

    for c_dir in candidate_conv_dirs:
        if os.path.realpath(c_dir) == os.path.realpath(master_conv_dir):
            continue
        for db_src in glob.glob(os.path.join(c_dir, "*.db")):
            fname = os.path.basename(db_src)
            db_dst = os.path.join(master_conv_dir, fname)
            if not os.path.exists(db_dst):
                try:
                    shutil.copy2(db_src, db_dst)
                    copied_dbs += 1
                except Exception:
                    pass

    for b_dir in candidate_brain_dirs:
        if os.path.realpath(b_dir) == os.path.realpath(master_brain_dir):
            continue
        for b_item in glob.glob(os.path.join(b_dir, "*")):
            b_name = os.path.basename(b_item)
            b_dst = os.path.join(master_brain_dir, b_name)
            if not os.path.exists(b_dst):
                try:
                    if os.path.isdir(b_item):
                        shutil.copytree(b_item, b_dst)
                    else:
                        shutil.copy2(b_item, b_dst)
                    copied_brains += 1
                except Exception:
                    pass
            elif os.path.isdir(b_item) and os.path.isdir(b_dst):
                for sub_p in [
                    os.path.join(".system_generated", "logs", "transcript_full.jsonl"),
                    os.path.join(".system_generated", "logs", "transcript.jsonl"),
                ]:
                    src_f = os.path.join(b_item, sub_p)
                    dst_f = os.path.join(b_dst, sub_p)
                    if os.path.isfile(src_f) and not os.path.isfile(dst_f):
                        try:
                            os.makedirs(os.path.dirname(dst_f), exist_ok=True)
                            shutil.copy2(src_f, dst_f)
                        except Exception:
                            pass

    # 3. Reconstruct or repair missing/incomplete .db files from transcripts
    reconstructed_dbs = 0
    all_brain_pools = set(candidate_brain_dirs)
    all_brain_pools.add(master_brain_dir)

    reconstructed_uuids = set()
    for b_pool in all_brain_pools:
        for b_item in glob.glob(os.path.join(b_pool, "*")):
            if not os.path.isdir(b_item):
                continue
            c_uuid = os.path.basename(b_item)
            if not re.match(r'^[0-9a-fA-F-]{36}$', c_uuid):
                continue
            if c_uuid in reconstructed_uuids:
                continue

            target_db = os.path.join(master_conv_dir, f"{c_uuid}.db")
            tf = os.path.join(b_item, ".system_generated", "logs", "transcript_full.jsonl")
            if not os.path.isfile(tf):
                tf = os.path.join(b_item, ".system_generated", "logs", "transcript.jsonl")

            if os.path.isfile(tf):
                if not os.path.exists(target_db) or is_synthesized_db_incomplete(target_db) or force_rebuild:
                    if synthesize_db_from_transcript(c_uuid, target_db, tf):
                        reconstructed_dbs += 1
                        reconstructed_uuids.add(c_uuid)

    # 4. Read and Synchronize conversation_summaries.db
    all_summaries = {}  # uuid -> pure_bin
    con = sqlite3.connect(master_sum_db)
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS conversation_summaries (
        conversation_id text PRIMARY KEY,
        title text NOT NULL DEFAULT "",
        preview text NOT NULL DEFAULT "",
        step_count integer NOT NULL DEFAULT 0,
        last_modified_time datetime NOT NULL,
        workspace_uris text NOT NULL DEFAULT "",
        status text NOT NULL DEFAULT "CASCADE_RUN_STATUS_IDLE",
        source text NOT NULL DEFAULT "",
        project_id text NOT NULL DEFAULT "",
        agent_name text NOT NULL DEFAULT "",
        parent_conversation_id text NOT NULL DEFAULT "",
        nesting_depth integer NOT NULL DEFAULT 0,
        battle_id text NOT NULL DEFAULT "",
        winning_conversation_id text NOT NULL DEFAULT "",
        not_fully_idle numeric NOT NULL DEFAULT false,
        killed numeric NOT NULL DEFAULT false,
        last_user_input_time datetime NOT NULL,
        last_user_input_step_index integer NOT NULL DEFAULT -1,
        app_data_dir text NOT NULL DEFAULT "antigravity",
        raw_summary blob,
        group_id text NOT NULL DEFAULT ""
    );''')
    con.commit()

    # Ingest from all discovered conversation_summaries.db candidates across the system
    sum_db_candidates = set()
    for c_dir in candidate_conv_dirs:
        cand_p = os.path.join(c_dir, "conversation_summaries.db")
        if os.path.exists(cand_p) and not os.path.islink(cand_p) and os.path.realpath(cand_p) != os.path.realpath(master_sum_db):
            sum_db_candidates.add(cand_p)
    sub_sum_db = os.path.join(master_conv_dir, "conversation_summaries.db")
    if os.path.exists(sub_sum_db) and not os.path.islink(sub_sum_db) and os.path.realpath(sub_sum_db) != os.path.realpath(master_sum_db):
        sum_db_candidates.add(sub_sum_db)

    for s_db in sorted(sum_db_candidates):
        try:
            s_con = sqlite3.connect(s_db)
            s_rows = s_con.cursor().execute("SELECT conversation_id, title, preview, step_count, last_modified_time, raw_summary FROM conversation_summaries;").fetchall()
            s_con.close()
            for r in s_rows:
                if r[5] or r[1]:
                    cur.execute('''INSERT OR REPLACE INTO conversation_summaries (
                        conversation_id, title, preview, step_count, last_modified_time, raw_summary
                    ) VALUES (?, ?, ?, ?, ?, ?)''', (r[0], r[1], r[2], r[3], r[4], r[5]))
            con.commit()
            try:
                os.rename(s_db, f"{s_db}.bak_{int(time.time())}")
                os.symlink(master_sum_db, s_db)
            except Exception:
                pass
        except Exception:
            pass

    rows = cur.execute("SELECT conversation_id, title, preview, step_count, last_modified_time, raw_summary FROM conversation_summaries;").fetchall()
    existing_rows = {r[0]: (r[1], r[2], r[3], r[4], r[5]) for r in rows}
    for r in rows:
        if r[5]:
            all_summaries[r[0]] = r[5]

    repaired_db_rows = 0
    updated_db_rows = 0
    backfilled = 0

    all_dbs = glob.glob(os.path.join(master_conv_dir, "*.db"))

    for db_file in all_dbs:
        conv_id = os.path.basename(db_file)[:-3]
        if not re.match(r'^[0-9a-fA-F-]{36}$', conv_id):
            continue

        file_mtime = os.path.getmtime(db_file)
        file_mtime_iso = datetime.datetime.fromtimestamp(file_mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000+00:00")

        # Get actual step count from sqlite steps table
        actual_steps = 0
        try:
            c = sqlite3.connect(db_file)
            actual_steps = c.cursor().execute("SELECT count(*) FROM steps;").fetchone()[0]
            c.close()
        except Exception:
            pass

        transcript_file = os.path.join(master_brain_dir, conv_id, ".system_generated", "logs", "transcript.jsonl")
        if not os.path.isfile(transcript_file):
            for b_dir in candidate_brain_dirs:
                cand_tf = os.path.join(b_dir, conv_id, ".system_generated", "logs", "transcript.jsonl")
                if os.path.isfile(cand_tf):
                    transcript_file = cand_tf
                    break
        anno_title = get_annotation_title(master_gemini, conv_id, [os.path.join(h, ".gemini", "antigravity") for h in homes])

        if conv_id in existing_rows:
            curr_title, curr_prev, curr_sc, curr_lm, curr_raw = existing_rows[conv_id]
            parsed_raw = parse_cascade_summary(curr_raw) if curr_raw else {}
            raw_title = parsed_raw.get("title")
            raw_summary = parsed_raw.get("summary")

            final_title = anno_title or curr_title or raw_title
            final_prev = curr_prev or raw_summary

            # If title is empty or generic, extract authentic title from prompt or artifacts
            if not final_title or final_title.strip() == "" or final_title in ["Conversation", "Untitled Conversation"]:
                ext_t, ext_p = extract_conv_text(db_file, transcript_file)
                if ext_t:
                    final_title = ext_t
                    final_prev = ext_p or final_prev

            # If existing raw_summary had empty title, rebuild it
            curr_raw_title = parsed_raw.get("title") or parsed_raw.get("summary")
            needs_title_rebuild = bool(final_title and (not curr_raw_title or curr_raw_title in ["Conversation", "Untitled Conversation"]))

            if curr_raw and len(curr_raw) > 20 and not needs_title_rebuild:
                all_summaries[conv_id] = curr_raw
                if anno_title and curr_title != anno_title:
                    cur.execute("UPDATE conversation_summaries SET title=? WHERE conversation_id=?;", (anno_title, conv_id))
                    updated_db_rows += 1
                continue

            user_step = get_last_user_step_index(db_file, max(actual_steps, curr_sc))
            pure_bin = build_cascade_summary(conv_id, final_title, final_prev, max(actual_steps, curr_sc), file_mtime_iso, last_user_step=user_step)
            all_summaries[conv_id] = pure_bin
            cur.execute('''UPDATE conversation_summaries
                           SET title=?, preview=?, step_count=?, last_modified_time=?, raw_summary=?, last_user_input_step_index=?
                           WHERE conversation_id=?;''',
                        (final_title, final_prev, max(actual_steps, curr_sc), file_mtime_iso, pure_bin, user_step, conv_id))
            updated_db_rows += 1
        else:
            if actual_steps == 0 and not anno_title and not os.path.isfile(transcript_file):
                continue
            ext_title, ext_prev = extract_conv_text(db_file, transcript_file)
            final_title = anno_title or ext_title
            if not final_title or final_title in ["Conversation", "Untitled Conversation"]:
                if actual_steps > 0:
                    final_title = f"Conversation ({conv_id[:8]})"
                elif os.path.isfile(transcript_file) or anno_title:
                    final_title = "Conversation"
                else:
                    continue
            final_prev = ext_prev or final_title
            user_step = get_last_user_step_index(db_file, actual_steps)
            pure_bin = build_cascade_summary(conv_id, final_title, final_prev, max(1, actual_steps), file_mtime_iso, last_user_step=user_step)
            all_summaries[conv_id] = pure_bin

            try:
                cur.execute('''INSERT OR REPLACE INTO conversation_summaries (
                    conversation_id, title, preview, step_count, last_modified_time,
                    workspace_uris, status, source, project_id, agent_name,
                    parent_conversation_id, nesting_depth, battle_id, winning_conversation_id,
                    not_fully_idle, killed, last_user_input_time, last_user_input_step_index,
                    app_data_dir, raw_summary, group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                    conv_id, final_title, final_prev, max(1, actual_steps), file_mtime_iso,
                    "", "CASCADE_RUN_STATUS_IDLE", "", "outside-of-project", "",
                    "", 0, "", "", 0, 0, file_mtime_iso, user_step,
                    "antigravity", pure_bin, ""
                ))
                backfilled += 1
            except Exception:
                pass

    con.commit()

    # 4. Ingest from state.vscdb (IDE Store)
    vscdb_path = os.path.join(real_home, ".config", "Antigravity IDE", "User", "globalStorage", "state.vscdb")
    vsc_ingested = 0
    if os.path.exists(vscdb_path):
        try:
            v_con = sqlite3.connect(vscdb_path)
            v_cur = v_con.cursor()
            v_cur.execute("SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync.trajectorySummaries';")
            v_row = v_cur.fetchone()
            if v_row and v_row[0]:
                raw_ide = base64.b64decode(v_row[0])
                vsc_entries = extract_entries_from_proto(raw_ide)
                for u_id, p_bin in vsc_entries.items():
                    parsed = parse_cascade_summary(p_bin)
                    ide_title = parsed.get("summary") or parsed.get("title")
                    ide_sc = parsed.get(2, 1)
                    ide_lm = parsed.get("last_modified_time")
                    ide_ct = parsed.get("created_time")

                    if ide_sc == 0 or (not ide_title) or ide_title in ["Conversation", "Untitled Conversation"] and ide_sc <= 1:
                        continue

                    db_p = os.path.join(master_conv_dir, f"{u_id}.db")
                    if not os.path.exists(db_p):
                        continue

                    if not ide_lm:
                        ide_lm = int(os.path.getmtime(db_p))

                    ide_lm_iso = datetime.datetime.fromtimestamp(ide_lm, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000+00:00") if ide_lm else "2026-01-01 00:00:00.000000+00:00"
                    ide_ct_iso = datetime.datetime.fromtimestamp(ide_ct, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000+00:00") if ide_ct else ide_lm_iso

                    if u_id not in all_summaries:
                        u_title = ide_title or "IDE Conversation"
                        u_prev = u_title
                        user_step = get_last_user_step_index(db_p, ide_sc)
                        fixed_bin = build_cascade_summary(u_id, u_title, u_prev, ide_sc, ide_lm_iso, ide_ct_iso, last_user_step=user_step)
                        all_summaries[u_id] = fixed_bin
                        vsc_ingested += 1
                        cur.execute('''INSERT OR IGNORE INTO conversation_summaries (
                            conversation_id, title, preview, step_count, last_modified_time,
                            workspace_uris, status, source, project_id, agent_name,
                            parent_conversation_id, nesting_depth, battle_id, winning_conversation_id,
                            not_fully_idle, killed, last_user_input_time, last_user_input_step_index,
                            app_data_dir, raw_summary, group_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                            u_id, u_title, u_prev, ide_sc, ide_lm_iso,
                            "", "CASCADE_RUN_STATUS_IDLE", "", "outside-of-project", "",
                            "", 0, "", "", 0, 0, ide_lm_iso, user_step,
                            "antigravity", fixed_bin, ""
                        ))
                    else:
                        curr_parsed = parse_cascade_summary(all_summaries[u_id])
                        curr_t = curr_parsed.get("title") or curr_parsed.get("summary")
                        if ide_title and (not curr_t or curr_t in ["Conversation", "IDE Conversation", "Untitled Conversation"]):
                            cur.execute("UPDATE conversation_summaries SET title=? WHERE conversation_id=?", (ide_title, u_id))
            v_con.close()
            if vsc_ingested:
                con.commit()
        except Exception:
            pass
            pass
    # 5. Write Unified SummariesState (Format A) to all LS proto paths
    summaries_state_bin = build_summaries_state(all_summaries)

    master_hub_pb = os.path.join(master_gemini, "agyhub_summaries.pb")
    master_hub_proto_pb = os.path.join(master_gemini, "agyhub_summaries_proto.pb")
    master_jet_pb = os.path.join(master_gemini, "jetbox_summaries.pb")
    master_jet_proto_pb = os.path.join(master_gemini, "jetbox_summaries_proto.pb")

    for p in [master_hub_pb, master_hub_proto_pb, master_jet_pb, master_jet_proto_pb]:
        try:
            if os.path.islink(p):
                os.unlink(p)
            tmp_p = p + ".tmp"
            with open(tmp_p, "wb") as f:
                f.write(summaries_state_bin)
            os.replace(tmp_p, p)
        except Exception:
            pass

    # 7. Setup IDE directory symlinks and proto files for shared IDEs
    ide_candidates = [
        os.path.join(real_home, ".gemini", "antigravity-ide"),
        os.path.join(real_home, ".gemini", "antigravity-cli"),
        os.path.join(real_home, ".gemini", "antigravity-acp"),
        os.path.join(real_home, ".gemini-ide", "antigravity-ide"),
        os.path.join(real_home, ".gemide", "antigravity-ide"),
    ]
    for h in homes:
        ide_candidates.extend(glob.glob(os.path.join(h, ".gemini", "antigravity*")))
        ide_candidates.extend(glob.glob(os.path.join(h, ".gemini*")))
        ide_candidates.extend(glob.glob(os.path.join(h, ".antigravity*")))

    target_ide_dirs = []
    for td in sorted(set(ide_candidates)):
        if os.path.isdir(td) and os.path.realpath(td) != os.path.realpath(master_gemini):
            target_ide_dirs.append(td)

    for target_dir in target_ide_dirs:
        os.makedirs(target_dir, exist_ok=True)

        for link_name, master_path in [
            ("conversations", master_conv_dir),
            ("brain", master_brain_dir),
            ("annotations", os.path.join(master_gemini, "annotations")),
            ("conversation_summaries.db", master_sum_db),
        ]:
            dst_link = os.path.join(target_dir, link_name)
            if not os.path.islink(dst_link):
                if os.path.exists(dst_link):
                    if os.path.isdir(dst_link):
                        bak_path = f"{dst_link}.bak_{int(time.time())}"
                        try:
                            os.rename(dst_link, bak_path)
                        except Exception:
                            pass
                    else:
                        try:
                            os.remove(dst_link)
                        except Exception:
                            pass
                try:
                    os.symlink(master_path, dst_link)
                except Exception:
                    pass

        for extra in ["conversation_summaries.db-shm", "conversation_summaries.db-wal"]:
            ide_extra = os.path.join(target_dir, extra)
            if os.path.islink(ide_extra) and not os.path.exists(os.path.realpath(ide_extra)):
                try:
                    os.unlink(ide_extra)
                except Exception:
                    pass

        for pb_name in ["jetbox_summaries.pb", "jetbox_summaries_proto.pb", "agyhub_summaries.pb", "agyhub_summaries_proto.pb"]:
            ide_pb = os.path.join(target_dir, pb_name)
            target = os.path.join(master_gemini, pb_name)
            if not os.path.islink(ide_pb):
                if os.path.exists(ide_pb):
                    os.remove(ide_pb)
                try:
                    os.symlink(target, ide_pb)
                except Exception:
                    pass

    # 8. Write Unified State Sync (Format B) to all IDE state.vscdb files
    vscdb_targets = [
        os.path.join(real_home, ".config", "Antigravity IDE", "User", "globalStorage", "state.vscdb"),
        os.path.join(real_home, ".config", "Antigravity", "User", "globalStorage", "state.vscdb"),
    ]
    for h in homes:
        vscdb_targets.extend(glob.glob(os.path.join(h, ".config", "*antigravity*", "**", "state.vscdb"), recursive=True))
        vscdb_targets.extend(glob.glob(os.path.join(h, ".config", "*Antigravity*", "**", "state.vscdb"), recursive=True))
        vscdb_targets.extend(glob.glob(os.path.join(h, ".antigravity*", "**", "state.vscdb"), recursive=True))

    unified_vsc_bin = build_unified_state_sync(all_summaries)
    unified_b64 = base64.b64encode(unified_vsc_bin).decode('ascii')

    for vp in sorted(set(vscdb_targets)):
        if os.path.exists(vp):
            try:
                v_con = sqlite3.connect(vp)
                v_cur = v_con.cursor()
                v_cur.execute("INSERT OR REPLACE INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync.trajectorySummaries', ?);", (unified_b64,))
                v_con.commit()
                v_con.close()
            except Exception:
                pass

    # 9. Sync conversation layouts in Desktop App storage.json
    app_storage_path = os.path.join(real_home, ".config", "Antigravity", "app_storage.json")
    if os.path.exists(app_storage_path):
        try:
            with open(app_storage_path, "r", encoding="utf-8") as f:
                storage_data = json.load(f)
            updated_storage = False
            for u_id in all_summaries.keys():
                layout_key = f"antigravity-multi-conversation-layout-v3-{u_id}"
                if layout_key not in storage_data:
                    storage_data[layout_key] = json.dumps({
                        "rootNode": {"type": "pane", "id": "pane-1", "cascadeId": u_id},
                        "focusedPaneId": "pane-1"
                    })
                    updated_storage = True
            if updated_storage:
                tmp_s = app_storage_path + ".tmp"
                with open(tmp_s, "w", encoding="utf-8") as f:
                    json.dump(storage_data, f)
                os.replace(tmp_s, app_storage_path)
        except Exception:
            pass

    # Also sync to clone profile app_storage if existing
    for p_dir in glob.glob(os.path.join(real_home, ".antigravity-profile*")):
        p_storage = os.path.join(p_dir, ".config", "Antigravity", "app_storage.json")
        if os.path.exists(p_storage):
            try:
                with open(p_storage, "r", encoding="utf-8") as f:
                    p_data = json.load(f)
                up_p = False
                for u_id in all_summaries.keys():
                    layout_key = f"antigravity-multi-conversation-layout-v3-{u_id}"
                    if layout_key not in p_data:
                        p_data[layout_key] = json.dumps({
                            "rootNode": {"type": "pane", "id": "pane-1", "cascadeId": u_id},
                            "focusedPaneId": "pane-1"
                        })
                        up_p = True
                if up_p:
                    tmp_p = p_storage + ".tmp"
                    with open(tmp_p, "w", encoding="utf-8") as f:
                        json.dump(p_data, f)
                    os.replace(tmp_p, p_storage)
            except Exception:
                pass

    total_summaries = cur.execute("SELECT count(*) FROM conversation_summaries;").fetchone()[0]
    con.close()

    if not quiet:
        print(f"========================================================================================")
        print(f"                       Antigravity History Synchronization Report                       ")
        print(f"========================================================================================")
        print(f"  • History Pools Scanned:      {len(candidate_conv_dirs)} conv stores, {len(candidate_brain_dirs)} brain stores")
        print(f"  • DB Files Merged:            {copied_dbs} new databases imported")
        print(f"  • Brain Folders Merged:       {copied_brains} new project folders imported")
        print(f"  • Databases Reconstructed:    {reconstructed_dbs} SQLite databases built from transcript logs")
        print(f"  • Summaries Backfilled:       {backfilled} newly indexed conversations")
        print(f"  • Conversations Updated:      {updated_db_rows} existing chats refreshed with authentic titles")
        print(f"  • IDE state.vscdb Ingested:   {vsc_ingested} conversations from IDE")
        print(f"  • Total Active History:       {len(all_summaries)} conversations synchronized")
        print(f"  • Target Stores Updated:      Desktop App, IDE state.vscdb, SQLite DB, Protobuf Files")
        print(f"========================================================================================")

    return {
        "conv_pools": len(candidate_conv_dirs),
        "brain_pools": len(candidate_brain_dirs),
        "copied_dbs": copied_dbs,
        "copied_brains": copied_brains,
        "reconstructed_dbs": reconstructed_dbs,
        "backfilled": backfilled,
        "updated": updated_db_rows,
        "total_summaries": len(all_summaries),
    }

def watch_mode(master_gemini=None):
    real_home = os.environ.get("REAL_HOME", os.path.expanduser("~"))
    if not master_gemini:
        master_gemini = os.path.join(real_home, ".gemini", "antigravity")

    master_conv_dir = os.path.join(master_gemini, "conversations")

    watch_paths = [
        os.path.join(master_gemini, "agyhub_summaries.pb"),
        os.path.join(master_gemini, "agyhub_summaries_proto.pb"),
        os.path.join(master_gemini, "conversation_summaries.db"),
        os.path.join(master_gemini, "conversation_summaries.db-wal"),
        os.path.join(real_home, ".config", "Antigravity IDE", "User", "globalStorage", "state.vscdb"),
        os.path.join(real_home, ".config", "Antigravity IDE", "User", "globalStorage", "state.vscdb-wal"),
        os.path.join(real_home, ".config", "Antigravity", "app_storage.json"),
        os.path.join(real_home, ".gemini-ide", "jetski-standalone-oauth-token"),
        os.path.join(real_home, ".gemide", "jetski-standalone-oauth-token"),
    ]

    def get_current_mtimes():
        m = {}
        for p in watch_paths:
            if os.path.exists(p):
                try:
                    m[p] = os.path.getmtime(p)
                except Exception:
                    pass
        # Live watch on all conversation databases
        for db_file in glob.glob(os.path.join(master_conv_dir, "*.db")):
            try:
                m[db_file] = os.path.getmtime(db_file)
            except Exception:
                pass
        # Live watch on all annotation files for prompt/title changes
        for anno_file in glob.glob(os.path.join(master_gemini, "annotations", "*.pbtxt")):
            try:
                m[anno_file] = os.path.getmtime(anno_file)
            except Exception:
                pass
        return m

    # Initial sync and token check on daemon start
    refresh_ide_oauth_token()
    merge_histories(master_gemini=master_gemini, quiet=True)
    last_mtimes = get_current_mtimes()

    while True:
        time.sleep(2)
        try:
            refresh_ide_oauth_token()
            curr = get_current_mtimes()
            if curr != last_mtimes:
                time.sleep(0.5)  # Debounce active SQLite file writes
                merge_histories(master_gemini=master_gemini, quiet=True)
                last_mtimes = get_current_mtimes()
        except Exception:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antigravity History Merger")
    parser.add_argument("--master", help="Path to master antigravity directory")
    parser.add_argument("--source", help="Source directory containing conversations or profile")
    parser.add_argument("--target", help="Target master antigravity directory")
    parser.add_argument("--quiet", action="store_true", help="Quiet output")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild of SQLite databases from transcripts")
    parser.add_argument("--watch", action="store_true", help="Run continuously in background and auto-sync on changes")
    args = parser.parse_args()

    if args.watch:
        watch_mode(master_gemini=args.master)
    else:
        merge_histories(master_gemini=args.master, source_dir=args.source, target_dir=args.target, quiet=args.quiet, force_rebuild=args.rebuild)
