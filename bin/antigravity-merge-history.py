#!/usr/bin/env python3
# ==============================================================================
# Antigravity Multi-Instance History Merger & Summary Backfiller
# Merges conversations and brain artifacts across App and IDE profiles.
# Backfills missing rows in conversation_summaries.db with prompt previews.
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
import argparse

def encode_varint(value):
    out = bytearray()
    while value > 0x7f:
        out.append((value & 0x7f) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)

def parse_proto_map(data):
    entries = {}
    other_fields = []
    pos = 0
    total = len(data)
    while pos < total:
        tag = data[pos]
        pos += 1
        length = 0
        shift = 0
        while pos < total:
            b = data[pos]
            pos += 1
            length |= (b & 0x7f) << shift
            if (b & 0x80) == 0:
                break
            shift += 7
        if pos + length > total:
            break
        field_data = data[pos:pos+length]
        pos += length
        if tag == 0x0a and len(field_data) > 38 and field_data[0] == 0x0a and field_data[1] == 0x24:
            uuid = field_data[2:38].decode('ascii', 'ignore')
            entries[uuid] = field_data
        else:
            other_fields.append((tag, field_data))
    return entries, other_fields

def merge_histories(master_gemini=None, quiet=False):
    real_home = os.environ.get("REAL_HOME", os.path.expanduser("~"))
    if not master_gemini:
        master_gemini = os.path.join(real_home, ".gemini", "antigravity")

    master_conv_dir = os.path.join(master_gemini, "conversations")
    master_brain_dir = os.path.join(master_gemini, "brain")
    master_sum_db = os.path.join(master_gemini, "conversation_summaries.db")

    os.makedirs(master_conv_dir, exist_ok=True)
    os.makedirs(master_brain_dir, exist_ok=True)

    if not os.path.isfile(master_sum_db):
        # Create table if missing
        con = sqlite3.connect(master_sum_db)
        con.execute('''CREATE TABLE IF NOT EXISTS conversation_summaries (
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
        con.close()

    # 1. Discover all profile pools
    pools = []
    # Master IDE
    ide_gemini = os.path.join(real_home, ".gemini", "antigravity-ide")
    if os.path.isdir(ide_gemini) and not os.path.islink(ide_gemini):
        pools.append(("ide-master", ide_gemini, "antigravity-ide"))

    # App profiles (~/.antigravity-profile*)
    for p_dir in glob.glob(os.path.join(real_home, ".antigravity-profile*")):
        c_dir = os.path.join(p_dir, ".gemini", "antigravity")
        if os.path.isdir(c_dir) and not os.path.islink(c_dir):
            pools.append((os.path.basename(p_dir), c_dir, "antigravity"))

    # IDE profiles (~/.antigravity-ide-profile*)
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

    # Copy from conversations.bak if present
    bak_conv = os.path.join(ide_gemini, "conversations.bak")
    if os.path.isdir(bak_conv):
        for f in os.listdir(bak_conv):
            src = os.path.join(bak_conv, f)
            dst = os.path.join(master_conv_dir, f)
            if not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                    copied_dbs += 1
                except Exception:
                    pass

    bak_brain = os.path.join(ide_gemini, "brain.bak")
    if os.path.isdir(bak_brain):
        for b_item in glob.glob(os.path.join(bak_brain, "*")):
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

    # 3. Backfill conversation_summaries.db
    con = sqlite3.connect(master_sum_db)
    cur = con.cursor()
    existing_ids = set(r[0] for r in cur.execute("SELECT conversation_id FROM conversation_summaries;").fetchall())

    all_dbs = glob.glob(os.path.join(master_conv_dir, "*.db"))
    missing_ids = [os.path.basename(f)[:-3] for f in all_dbs if os.path.basename(f)[:-3] not in existing_ids]

    backfilled = 0
    for conv_id in missing_ids:
        db_file = os.path.join(master_conv_dir, f"{conv_id}.db")
        transcript_file = os.path.join(master_brain_dir, conv_id, ".system_generated", "logs", "transcript.jsonl")

        preview = ""
        title = ""
        created_at = ""
        last_modified_time = ""
        step_count = 0
        project_id = "outside-of-project"
        app_tag = "antigravity"

        # Read transcript if available
        if os.path.isfile(transcript_file):
            try:
                with open(transcript_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                        except Exception:
                            continue
                        step_count += 1
                        t = data.get("created_at", "")
                        if t:
                            last_modified_time = t
                        if data.get("step_index") == 0 and not preview:
                            content = data.get("content", "")
                            m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                            if m:
                                req = m.group(1).strip()
                                preview = " ".join(req.split())[:120]
                                title = req.split("\n")[0].strip()[:40]
                            else:
                                clean = " ".join(content.split())[:120]
                                preview = clean
                                title = clean[:40]
                            created_at = t
            except Exception:
                pass

        # Inspect database if transcript missing or incomplete
        if not step_count and os.path.isfile(db_file):
            try:
                c = sqlite3.connect(db_file)
                step_count = c.cursor().execute("SELECT count(*) FROM steps;").fetchone()[0]
                c.close()
            except Exception:
                pass

        if not created_at and os.path.isfile(db_file):
            mtime = os.path.getmtime(db_file)
            created_at = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000+00:00")
        if not last_modified_time:
            last_modified_time = created_at

        # Insert record
        try:
            cur.execute('''INSERT OR REPLACE INTO conversation_summaries (
                conversation_id, title, preview, step_count, last_modified_time,
                workspace_uris, status, source, project_id, agent_name,
                parent_conversation_id, nesting_depth, battle_id, winning_conversation_id,
                not_fully_idle, killed, last_user_input_time, last_user_input_step_index,
                app_data_dir, raw_summary, group_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                conv_id, title, preview, step_count, last_modified_time,
                "", "CASCADE_RUN_STATUS_IDLE", "", project_id, "",
                "", 0, "", "", 0, 0, created_at, -1,
                app_tag, None, ""
            ))
            backfilled += 1
        except Exception:
            pass

    con.commit()

    # 4. Two-Way Protobuf & VS Code State Sync (App <-> IDE Bridge)
    proto_synced = 0
    try:
        app_proto_path = os.path.join(master_gemini, "agyhub_summaries_proto.pb")
        vscdb_path = os.path.join(real_home, ".config", "Antigravity IDE", "User", "globalStorage", "state.vscdb")

        app_entries = {}
        other_fields = []
        if os.path.exists(app_proto_path):
            with open(app_proto_path, "rb") as f:
                app_entries, other_fields = parse_proto_map(f.read())

        ide_entries = {}
        if os.path.exists(vscdb_path):
            v_con = sqlite3.connect(vscdb_path)
            v_cur = v_con.cursor()
            v_cur.execute("SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync.trajectorySummaries';")
            v_row = v_cur.fetchone()
            if v_row and v_row[0]:
                raw_ide = base64.b64decode(v_row[0])
                ide_entries, _ = parse_proto_map(raw_ide)

            merged_entries = dict(ide_entries)
            merged_entries.update(app_entries)
            proto_synced = len(merged_entries)

            unified_bin = bytearray()
            for u_id, f_data in merged_entries.items():
                unified_bin.append(0x0a)
                unified_bin.extend(encode_varint(len(f_data)))
                unified_bin.extend(f_data)
            for tag, f_data in other_fields:
                unified_bin.append(tag)
                unified_bin.extend(encode_varint(len(f_data)))
                unified_bin.extend(f_data)

            with open(app_proto_path, "wb") as f:
                f.write(unified_bin)

            unified_b64 = base64.b64encode(unified_bin).decode('ascii')
            v_cur.execute("UPDATE ItemTable SET value = ? WHERE key = 'antigravityUnifiedStateSync.trajectorySummaries';", (unified_b64,))
            v_con.commit()
            v_con.close()

        for sym_name in ["agyhub_summaries_proto.pb", "jetbox_summaries_proto.pb", "jetbox_summaries.pb"]:
            sym_path = os.path.join(ide_gemini, sym_name)
            if os.path.exists(sym_path) and not os.path.islink(sym_path):
                os.remove(sym_path)
            if not os.path.islink(sym_path) and os.path.exists(app_proto_path):
                os.symlink(app_proto_path, sym_path)
    except Exception:
        pass

    total_summaries = cur.execute("SELECT count(*) FROM conversation_summaries;").fetchone()[0]
    app_count = cur.execute("SELECT count(*) FROM conversation_summaries WHERE app_data_dir='antigravity';").fetchone()[0]
    ide_count = cur.execute("SELECT count(*) FROM conversation_summaries WHERE app_data_dir='antigravity-ide';").fetchone()[0]
    con.close()

    if not quiet:
        print(f"========================================================================================")
        print(f"                       Antigravity History Synchronization Report                       ")
        print(f"========================================================================================")
        print(f"  • Source Pools Scanned:       {len(pools) + 1} pools")
        print(f"  • DB Files Merged:            {copied_dbs} new databases imported")
        print(f"  • Brain Folders Merged:       {copied_brains} new project folders imported")
        print(f"  • Summaries Backfilled:       {backfilled} newly indexed conversations")
        print(f"  • Total Active History:       {total_summaries} conversations indexed")
        print(f"      - Antigravity App:        {app_count} conversations")
        print(f"      - Antigravity IDE:        {ide_count} conversations")
        print(f"========================================================================================")

    return {
        "pools_scanned": len(pools) + 1,
        "copied_dbs": copied_dbs,
        "copied_brains": copied_brains,
        "backfilled": backfilled,
        "total_summaries": total_summaries,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antigravity History Merger")
    parser.add_argument("--master", help="Path to master antigravity directory")
    parser.add_argument("--quiet", action="store_true", help="Quiet output")
    args = parser.parse_args()

    merge_histories(master_gemini=args.master, quiet=args.quiet)
