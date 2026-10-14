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

def build_cascade_summary(uuid_str, title, summary_text, step_count=1, mtime_iso="", created_iso=""):
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
      Field 16: trajectory_type (1)
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
    out.extend(encode_tag_uint(22, 1))

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

def extract_conv_text(db_path, transcript_path):
    """Extracts (title, preview) from transcript and sqlite steps."""
    first_user_prompt = ""
    latest_user_prompt = ""

    if os.path.isfile(transcript_path):
        try:
            with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    content = data.get("content", "")
                    step_type = data.get("type", "")
                    if step_type == "USER_INPUT" and content:
                        m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                        req = m.group(1).strip() if m else content.strip()
                        clean = " ".join(req.split())
                        if not first_user_prompt:
                            first_user_prompt = clean
                        latest_user_prompt = clean
        except Exception:
            pass

    if not latest_user_prompt and os.path.isfile(db_path):
        try:
            c = sqlite3.connect(db_path)
            cur = c.cursor()
            rows = cur.execute("SELECT idx, step_payload FROM steps WHERE step_type = 14 ORDER BY idx ASC;").fetchall()
            c.close()
            for r_idx, payload in rows:
                if not payload: continue
                m = re.search(rb"<USER_REQUEST>(.*?)</USER_REQUEST>", payload, re.DOTALL)
                if m:
                    try:
                        clean = " ".join(m.group(1).decode("utf-8", "ignore").split())
                        if clean:
                            if not first_user_prompt:
                                first_user_prompt = clean
                            latest_user_prompt = clean
                            break
                    except Exception:
                        pass
        except Exception:
            pass

    title = first_user_prompt[:50] if first_user_prompt else ""
    preview = latest_user_prompt[:200] if latest_user_prompt else ""
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

def merge_histories(master_gemini=None, quiet=False):
    real_home = os.environ.get("REAL_HOME", os.path.expanduser("~"))
    if not master_gemini:
        master_gemini = os.path.join(real_home, ".gemini", "antigravity")

    master_conv_dir = os.path.join(master_gemini, "conversations")
    master_brain_dir = os.path.join(master_gemini, "brain")
    master_sum_db = os.path.join(master_gemini, "conversation_summaries.db")

    os.makedirs(master_conv_dir, exist_ok=True)
    os.makedirs(master_brain_dir, exist_ok=True)

    # 1. Discover all profile pools
    pools = []
    ide_gemini = os.path.join(real_home, ".gemini", "antigravity-ide")
    if os.path.isdir(ide_gemini) and not os.path.islink(ide_gemini):
        pools.append(("ide-master", ide_gemini, "antigravity-ide"))

    for p_dir in glob.glob(os.path.join(real_home, ".antigravity-profile*")):
        c_dir = os.path.join(p_dir, ".gemini", "antigravity")
        if os.path.isdir(c_dir) and not os.path.islink(c_dir):
            pools.append((os.path.basename(p_dir), c_dir, "antigravity"))

    for p_dir in glob.glob(os.path.join(real_home, ".antigravity-ide-profile*")):
        c_dir = os.path.join(p_dir, ".gemini", "antigravity-ide")
        if os.path.isdir(c_dir) and not os.path.islink(c_dir):
            pools.append((os.path.basename(p_dir), c_dir, "antigravity-ide"))

    # 2. Copy missing .db files and brain directories into master
    copied_dbs = 0
    copied_brains = 0

    for name, pool_dir, app_tag in pools:
        p_conv = os.path.join(pool_dir, "conversations")
        p_brain = os.path.join(pool_dir, "brain")

        if os.path.isdir(p_conv) and not os.path.islink(p_conv):
            for db_src in glob.glob(os.path.join(p_conv, "*.db")):
                fname = os.path.basename(db_src)
                db_dst = os.path.join(master_conv_dir, fname)
                if not os.path.exists(db_dst):
                    try:
                        shutil.copy2(db_src, db_dst)
                        copied_dbs += 1
                    except Exception:
                        pass

        if os.path.isdir(p_brain) and not os.path.islink(p_brain):
            for b_item in glob.glob(os.path.join(p_brain, "*")):
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
    # 3. Read and Synchronize conversation_summaries.db
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

        if conv_id in existing_rows:
            curr_title, curr_prev, curr_sc, curr_lm, curr_raw = existing_rows[conv_id]
            parsed_raw = parse_cascade_summary(curr_raw)
            raw_title = parsed_raw.get("title")
            raw_summary = parsed_raw.get("summary")

            final_title = curr_title or raw_title
            final_prev = curr_prev or raw_summary

            needs_update = False
            if actual_steps > curr_sc:
                needs_update = True
            elif not raw_title or not raw_summary:
                needs_update = True
            elif not curr_title or not curr_prev:
                needs_update = True
            elif raw_summary != final_title:
                needs_update = True

            if needs_update or not final_title or not final_prev:
                ext_title, ext_prev = extract_conv_text(db_file, transcript_file)
                if not final_title:
                    final_title = ext_title or "Conversation"
                if not final_prev or actual_steps > curr_sc:
                    final_prev = ext_prev or final_title

            final_sc = max(actual_steps, curr_sc)
            final_lm = file_mtime_iso if actual_steps > curr_sc else curr_lm

            pure_bin = build_cascade_summary(conv_id, final_title, final_prev, final_sc, final_lm)
            all_summaries[conv_id] = pure_bin

            if needs_update or pure_bin != curr_raw:
                cur.execute('''UPDATE conversation_summaries
                               SET title=?, preview=?, step_count=?, last_modified_time=?, raw_summary=?
                               WHERE conversation_id=?;''',
                            (final_title, final_prev, final_sc, final_lm, pure_bin, conv_id))
                updated_db_rows += 1
        else:
            if actual_steps == 0:
                continue
            ext_title, ext_prev = extract_conv_text(db_file, transcript_file)
            if not ext_title or ext_title in ["Conversation", "Untitled Conversation"]:
                if not os.path.isfile(transcript_file):
                    continue
            final_title = ext_title or "Conversation"
            final_prev = ext_prev or final_title
            pure_bin = build_cascade_summary(conv_id, final_title, final_prev, actual_steps, file_mtime_iso)
            all_summaries[conv_id] = pure_bin

            try:
                cur.execute('''INSERT OR REPLACE INTO conversation_summaries (
                    conversation_id, title, preview, step_count, last_modified_time,
                    workspace_uris, status, source, project_id, agent_name,
                    parent_conversation_id, nesting_depth, battle_id, winning_conversation_id,
                    not_fully_idle, killed, last_user_input_time, last_user_input_step_index,
                    app_data_dir, raw_summary, group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                    conv_id, final_title, final_prev, actual_steps, file_mtime_iso,
                    "", "CASCADE_RUN_STATUS_IDLE", "", "outside-of-project", "",
                    "", 0, "", "", 0, 0, file_mtime_iso, -1,
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
                        fixed_bin = build_cascade_summary(u_id, u_title, u_prev, ide_sc, ide_lm_iso, ide_ct_iso)
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
                            "", 0, "", "", 0, 0, ide_lm_iso, -1,
                            "antigravity", fixed_bin, ""
                        ))
                    else:
                        curr_parsed = parse_cascade_summary(all_summaries[u_id])
                        curr_t = curr_parsed.get("title") or curr_parsed.get("summary")
                        curr_lm_sec = curr_parsed.get("last_modified_time")
                        if ide_title and (not curr_t or curr_t in ["Conversation", "IDE Conversation", "Untitled Conversation"]):
                            fixed_bin = build_cascade_summary(u_id, ide_title, ide_title, max(ide_sc, curr_parsed.get(2, 1)), mtime_iso=curr_lm_sec)
                            all_summaries[u_id] = fixed_bin
                            cur.execute("UPDATE conversation_summaries SET title=?, raw_summary=? WHERE conversation_id=?", (ide_title, fixed_bin, u_id))
            v_con.close()
            if vsc_ingested:
                con.commit()
        except Exception:
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

    # 7. Setup IDE directory symlinks and proto files
    os.makedirs(ide_gemini, exist_ok=True)

    ide_conv_link = os.path.join(ide_gemini, "conversations")
    if not os.path.islink(ide_conv_link):
        if os.path.exists(ide_conv_link):
            shutil.rmtree(ide_conv_link, ignore_errors=True)
        os.symlink(master_conv_dir, ide_conv_link)

    ide_brain_link = os.path.join(ide_gemini, "brain")
    if not os.path.islink(ide_brain_link):
        if os.path.exists(ide_brain_link):
            shutil.rmtree(ide_brain_link, ignore_errors=True)
        os.symlink(master_brain_dir, ide_brain_link)

    ide_db_link = os.path.join(ide_gemini, "conversation_summaries.db")
    if not os.path.islink(ide_db_link):
        if os.path.exists(ide_db_link):
            os.remove(ide_db_link)
        os.symlink(master_sum_db, ide_db_link)

    for extra in ["conversation_summaries.db-shm", "conversation_summaries.db-wal"]:
        ide_extra = os.path.join(ide_gemini, extra)
        if os.path.islink(ide_extra) and not os.path.exists(os.path.realpath(ide_extra)):
            try:
                os.unlink(ide_extra)
            except Exception:
                pass

    for pb_name in ["jetbox_summaries.pb", "jetbox_summaries_proto.pb", "agyhub_summaries.pb", "agyhub_summaries_proto.pb"]:
        ide_pb = os.path.join(ide_gemini, pb_name)
        target = os.path.join(master_gemini, pb_name)
        if not os.path.islink(ide_pb):
            if os.path.exists(ide_pb):
                os.remove(ide_pb)
            try:
                os.symlink(target, ide_pb)
            except Exception:
                pass

    # 8. Write Unified State Sync (Format B) to IDE state.vscdb
    if os.path.exists(vscdb_path):
        try:
            unified_vsc_bin = build_unified_state_sync(all_summaries)
            unified_b64 = base64.b64encode(unified_vsc_bin).decode('ascii')
            v_con = sqlite3.connect(vscdb_path)
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
        print(f"  • Source Pools Scanned:       {len(pools) + 1} pools")
        print(f"  • DB Files Merged:            {copied_dbs} new databases imported")
        print(f"  • Brain Folders Merged:       {copied_brains} new project folders imported")
        print(f"  • Summaries Backfilled:       {backfilled} newly indexed conversations")
        print(f"  • Conversations Updated:      {updated_db_rows} existing chats refreshed with new steps")
        print(f"  • IDE state.vscdb Ingested:   {vsc_ingested} conversations from IDE")
        print(f"  • Total Active History:       {len(all_summaries)} conversations synchronized")
        print(f"  • Target Stores Updated:      Desktop App, IDE state.vscdb, SQLite DB, Protobuf Files")
        print(f"========================================================================================")

    return {
        "pools_scanned": len(pools) + 1,
        "copied_dbs": copied_dbs,
        "copied_brains": copied_brains,
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
        return m

    # Initial sync on daemon start
    merge_histories(master_gemini=master_gemini, quiet=True)
    last_mtimes = get_current_mtimes()

    while True:
        time.sleep(2)
        try:
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
    parser.add_argument("--quiet", action="store_true", help="Quiet output")
    parser.add_argument("--watch", action="store_true", help="Run continuously in background and auto-sync on changes")
    args = parser.parse_args()

    if args.watch:
        watch_mode(master_gemini=args.master)
    else:
        merge_histories(master_gemini=args.master, quiet=args.quiet)
