#!/usr/bin/env python3
"""
Antigravity Cross-System Migration & Backup Tool
Supports:
  - export-history / import-history (Conversations, brains, summaries, annotations)
  - export-suite / import-suite (Rules, Skills, Plugins, MCP servers, Accounts & Tokens)
  - export-all / import-all (Unified bundle of History + Suite Configurations)
  - create-backup / list-backups / restore-backup (Safety backups with automated rollback protection)
"""

import os
import sys
import shutil
import tarfile
import json
import datetime
import glob
import argparse
import subprocess

REAL_USER = os.environ.get("REAL_USER")
if not REAL_USER:
    REAL_USER = os.environ.get("SUDO_USER") or os.environ.get("USER") or "root"

REAL_HOME = os.environ.get("REAL_HOME")
if not REAL_HOME:
    if REAL_USER and REAL_USER != "root":
        try:
            import pwd
            REAL_HOME = pwd.getpwnam(REAL_USER).pw_dir
        except Exception:
            REAL_HOME = os.path.expanduser("~")
    else:
        REAL_HOME = os.path.expanduser("~")

GEMINI_DIR = os.path.join(REAL_HOME, ".gemini")
MASTER_GEMINI = os.path.join(GEMINI_DIR, "antigravity")
CONFIG_DIR = os.path.join(GEMINI_DIR, "config")
AGENTS_DIR = os.path.join(REAL_HOME, ".agents")
ANTIGRAVITY_CONF_DIR = os.path.join(REAL_HOME, ".config", "antigravity")
BACKUPS_DIR = os.path.join(ANTIGRAVITY_CONF_DIR, "backups")
LOCAL_BIN = os.path.join(REAL_HOME, ".local", "bin")

GREEN = "\033[1;32m"
BLUE = "\033[1;38;5;75m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
CYAN = "\033[1;36m"
NC = "\033[0m"
BOLD = "\033[1m"

def log_info(msg):
    print(f"{BLUE}[INFO]{NC} {msg}")

def log_success(msg):
    print(f"{GREEN}[SUCCESS]{NC} {msg}")

def log_warn(msg):
    print(f"{YELLOW}[WARN]{NC} {msg}")

def log_err(msg):
    print(f"{RED}[ERROR]{NC} {msg}")

def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def format_size(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"

def safe_extract_tar(tar, path):
    """Safely extracts tar files preventing path traversal and handling Python 3.12+ filter."""
    try:
        tar.extractall(path=path, filter="data")
    except TypeError:
        tar.extractall(path=path)

def get_db_step_count(db_path):
    """Safely queries SQLite database step count for precedence comparison."""
    if not os.path.isfile(db_path):
        return -1
    try:
        import sqlite3
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as con:
            row = con.execute("SELECT count(*) FROM steps").fetchone()
            return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return -1

# ==============================================================================
# Safety Backup & Snapshot Functions
# ==============================================================================
def create_safety_backup(category="history", label="pre_change"):
    if not MASTER_GEMINI or not os.path.exists(MASTER_GEMINI):
        return None
    if os.environ.get("ANTIGRAVITY_TEST_MODE") == "1" or os.environ.get("ANTIGRAVITY_SKIP_SAFETY_BACKUP") == "1":
        return None
    cat_dir = os.path.join(BACKUPS_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)
    ts = get_timestamp()
    tar_name = f"{category}-{label}-{ts}.tar.gz"
    tar_path = os.path.join(cat_dir, tar_name)

    log_info(f"Creating safety snapshot in {tar_path}...")

    with tarfile.open(tar_path, "w:gz") as tar:
        if category in ["history", "all"]:
            # Master history items
            for item in ["conversations", "brain", "annotations"]:
                p = os.path.join(MASTER_GEMINI, item)
                if os.path.exists(p):
                    tar.add(p, arcname=os.path.join("history", item), recursive=True)
            for sum_f in glob.glob(os.path.join(MASTER_GEMINI, "*summaries*")):
                if os.path.isfile(sum_f):
                    tar.add(sum_f, arcname=os.path.join("history", os.path.basename(sum_f)))
            # Also backup any existing conversations.bak in antigravity-ide
            ide_conv_bak = os.path.join(GEMINI_DIR, "antigravity-ide", "conversations.bak")
            if os.path.isdir(ide_conv_bak):
                tar.add(ide_conv_bak, arcname="history/ide_conversations.bak", recursive=True)
            ide_brain_bak = os.path.join(GEMINI_DIR, "antigravity-ide", "brain.bak")
            if os.path.isdir(ide_brain_bak):
                tar.add(ide_brain_bak, arcname="history/ide_brain.bak", recursive=True)

        if category in ["suite", "configs", "all"]:
            # GEMINI.md global rules
            gemini_md = os.path.join(GEMINI_DIR, "GEMINI.md")
            if os.path.isfile(gemini_md):
                tar.add(gemini_md, arcname="suite/GEMINI.md")
            # Config dir (skills, plugins, projects, config.json, mcp_config.json)
            if os.path.isdir(CONFIG_DIR):
                tar.add(CONFIG_DIR, arcname="suite/config", recursive=True)
            # Agents dir (skills definitions)
            if os.path.isdir(AGENTS_DIR):
                tar.add(AGENTS_DIR, arcname="suite/agents", recursive=True)
            # MCP servers
            mcp_dir = os.path.join(MASTER_GEMINI, "mcp")
            if os.path.isdir(mcp_dir):
                tar.add(mcp_dir, arcname="suite/mcp", recursive=True)
            # Accounts & configs
            if os.path.isdir(ANTIGRAVITY_CONF_DIR):
                for conf_f in glob.glob(os.path.join(ANTIGRAVITY_CONF_DIR, "*.conf")):
                    tar.add(conf_f, arcname=os.path.join("suite", "config_antigravity", os.path.basename(conf_f)))
                accs_dir = os.path.join(ANTIGRAVITY_CONF_DIR, "accounts")
                if os.path.isdir(accs_dir):
                    tar.add(accs_dir, arcname="suite/accounts", recursive=True)
            # OAuth tokens
            token_targets = [
                (os.path.join(GEMINI_DIR, "jetski-standalone-oauth-token"), "gemini-token"),
                (os.path.join(REAL_HOME, ".antigravity-profile2", ".gemini", "jetski-standalone-oauth-token"), "acc2-token"),
                (os.path.join(REAL_HOME, ".gemini-ide", "jetski-standalone-oauth-token"), "gemini-ide-token"),
                (os.path.join(REAL_HOME, ".gemide", "jetski-standalone-oauth-token"), "gemide-token"),
            ]
            for token_path, token_arc in token_targets:
                if os.path.isfile(token_path):
                    tar.add(token_path, arcname=os.path.join("suite", "tokens", token_arc))

    size_str = format_size(os.path.getsize(tar_path))
    log_success(f"Safety snapshot created: {tar_name} ({size_str})")
    return tar_path

def list_all_backups():
    """Lists all available safety backups with dates and sizes."""
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    all_files = glob.glob(os.path.join(BACKUPS_DIR, "**", "*.tar.gz"), recursive=True)
    if not all_files:
        print(f"{YELLOW}No backups found in {BACKUPS_DIR}.{NC}")
        return []

    all_files.sort(key=os.path.getmtime, reverse=True)
    print(f"\n{CYAN}========================================================================================{NC}")
    print(f"{BOLD}{CYAN}                        Available Antigravity Backups & Snapshots                       {NC}")
    print(f"{CYAN}========================================================================================{NC}")
    print(f" {'#':<3} {'Filename':<48} {'Size':<10} {'Created Date'}")
    print(f"----------------------------------------------------------------------------------------")
    for idx, f in enumerate(all_files, 1):
        fn = os.path.basename(f)
        sz = format_size(os.path.getsize(f))
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M:%S")
        print(f" [{idx:<2}] {fn:<48} {sz:<10} {mtime}")
    print(f"{CYAN}========================================================================================{NC}")
    return all_files

def restore_backup(backup_path):
    """Restores files from a backup tarball."""
    if not os.path.isfile(backup_path):
        log_err(f"Backup file not found: {backup_path}")
        return False

    fn = os.path.basename(backup_path)
    log_info(f"Inspecting backup: {fn}...")

    # Determine category
    is_history = "history" in fn or "all" in fn
    is_suite = "suite" in fn or "configs" in fn or "all" in fn

    # Pre-restore safety snapshot
    create_safety_backup(category="all", label="pre_restore_snapshot")

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(backup_path, "r:*") as tar:
            safe_extract_tar(tar, path=tmpdir)

        # Restore History (support both history/ subfolder and root-level export)
        hist_dir = os.path.join(tmpdir, "history")
        if not os.path.isdir(hist_dir) and (os.path.isdir(os.path.join(tmpdir, "conversations")) or glob.glob(os.path.join(tmpdir, "*summaries*"))):
            hist_dir = tmpdir

        if os.path.isdir(hist_dir):
            log_info("Restoring conversation history, annotations, and brain artifacts...")
            src_conv = os.path.join(hist_dir, "conversations")
            dst_conv = os.path.join(MASTER_GEMINI, "conversations")
            os.makedirs(dst_conv, exist_ok=True)
            if os.path.isdir(src_conv):
                # Clean up post-backup conversations not present in snapshot
                snapshot_dbs = {os.path.basename(db) for db in glob.glob(os.path.join(src_conv, "*.db"))}
                for cur_db in glob.glob(os.path.join(dst_conv, "*.db")):
                    if os.path.basename(cur_db) not in snapshot_dbs:
                        try:
                            os.remove(cur_db)
                            for ext in ["-wal", "-shm"]:
                                if os.path.exists(f"{cur_db}{ext}"):
                                    os.remove(f"{cur_db}{ext}")
                        except Exception:
                            pass

                for db in glob.glob(os.path.join(src_conv, "*.db")):
                    db_name = os.path.basename(db)
                    dst_db = os.path.join(dst_conv, db_name)
                    shutil.copy2(db, dst_db)
                    for ext in ["-wal", "-shm"]:
                        s_wal = f"{db}{ext}"
                        d_wal = f"{dst_db}{ext}"
                        if os.path.exists(s_wal):
                            shutil.copy2(s_wal, d_wal)
                        elif os.path.exists(d_wal):
                            try: os.remove(d_wal)
                            except Exception: pass

            src_brain = os.path.join(hist_dir, "brain")
            dst_brain = os.path.join(MASTER_GEMINI, "brain")
            os.makedirs(dst_brain, exist_ok=True)
            if os.path.isdir(src_brain):
                for b_item in glob.glob(os.path.join(src_brain, "*")):
                    b_dst = os.path.join(dst_brain, os.path.basename(b_item))
                    if os.path.isdir(b_item):
                        shutil.copytree(b_item, b_dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(b_item, b_dst)

            src_anno = os.path.join(hist_dir, "annotations")
            dst_anno = os.path.join(MASTER_GEMINI, "annotations")
            os.makedirs(dst_anno, exist_ok=True)
            if os.path.isdir(src_anno):
                for a_item in glob.glob(os.path.join(src_anno, "*")):
                    shutil.copy2(a_item, os.path.join(dst_anno, os.path.basename(a_item)))

            # Prevent SQLite WAL/SHM corruption: remove existing WAL/SHM if not in backup
            for ext in ["-wal", "-shm"]:
                wal_path = os.path.join(MASTER_GEMINI, f"conversation_summaries.db{ext}")
                backup_wal = os.path.join(hist_dir, f"conversation_summaries.db{ext}")
                if os.path.exists(wal_path) and not os.path.exists(backup_wal):
                    try: os.remove(wal_path)
                    except Exception: pass

            for sum_f in glob.glob(os.path.join(hist_dir, "*summaries*")):
                shutil.copy2(sum_f, os.path.join(MASTER_GEMINI, os.path.basename(sum_f)))

            # Re-index history
            trigger_history_merge()

        # Restore Suite (support both suite/ subfolder and root-level export)
        suite_dir = os.path.join(tmpdir, "suite")
        if not os.path.isdir(suite_dir) and (os.path.isfile(os.path.join(tmpdir, "GEMINI.md")) or os.path.isdir(os.path.join(tmpdir, "config"))):
            suite_dir = tmpdir

        if os.path.isdir(suite_dir):
            log_info("Restoring suite configurations, rules, skills, and accounts...")
            src_gemini_md = os.path.join(suite_dir, "GEMINI.md")
            if os.path.isfile(src_gemini_md):
                shutil.copy2(src_gemini_md, os.path.join(GEMINI_DIR, "GEMINI.md"))

            src_cfg = os.path.join(suite_dir, "config")
            if os.path.isdir(src_cfg):
                shutil.copytree(src_cfg, CONFIG_DIR, dirs_exist_ok=True)

            src_agents = os.path.join(suite_dir, "agents")
            if os.path.isdir(src_agents):
                shutil.copytree(src_agents, AGENTS_DIR, dirs_exist_ok=True)

            src_mcp = os.path.join(suite_dir, "mcp")
            if os.path.isdir(src_mcp):
                shutil.copytree(src_mcp, os.path.join(MASTER_GEMINI, "mcp"), dirs_exist_ok=True)

            src_accs = os.path.join(suite_dir, "accounts")
            if os.path.isdir(src_accs):
                os.makedirs(os.path.join(ANTIGRAVITY_CONF_DIR, "accounts"), exist_ok=True)
                shutil.copytree(src_accs, os.path.join(ANTIGRAVITY_CONF_DIR, "accounts"), dirs_exist_ok=True)

            src_confs = os.path.join(suite_dir, "config_antigravity")
            if os.path.isdir(src_confs):
                for cf in glob.glob(os.path.join(src_confs, "*.conf")):
                    shutil.copy2(cf, os.path.join(ANTIGRAVITY_CONF_DIR, os.path.basename(cf)))

            tokens_src = os.path.join(suite_dir, "tokens")
            if os.path.isdir(tokens_src):
                token_restore_map = [
                    ("gemini-token", os.path.join(GEMINI_DIR, "jetski-standalone-oauth-token")),
                    (".gemini-token", os.path.join(GEMINI_DIR, "jetski-standalone-oauth-token")),
                    ("acc2-token", os.path.join(REAL_HOME, ".antigravity-profile2", ".gemini", "jetski-standalone-oauth-token")),
                    ("gemini-ide-token", os.path.join(REAL_HOME, ".gemini-ide", "jetski-standalone-oauth-token")),
                    (".gemini-ide-token", os.path.join(REAL_HOME, ".gemini-ide", "jetski-standalone-oauth-token")),
                    ("gemide-token", os.path.join(REAL_HOME, ".gemide", "jetski-standalone-oauth-token")),
                    (".gemide-token", os.path.join(REAL_HOME, ".gemide", "jetski-standalone-oauth-token")),
                ]
                for src_name, dst_path in token_restore_map:
                    token_src_file = os.path.join(tokens_src, src_name)
                    if os.path.isfile(token_src_file):
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        shutil.copy2(token_src_file, dst_path)
                        try:
                            os.chmod(dst_path, 0o600)
                        except Exception:
                            pass
                        log_success(f"Restored OAuth token to {dst_path}")

    log_success(f"Restore from {fn} completed successfully!")
    return True

# ==============================================================================
# Export Functions
# ==============================================================================
def export_history(output_path=None):
    """Exports all conversation history, brain artifacts, summaries, and annotations."""
    if not output_path:
        ts = get_timestamp()
        output_path = os.path.join(REAL_HOME, f"antigravity-history-export-{ts}.tar.gz")

    output_path = os.path.abspath(os.path.expanduser(output_path))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    log_info(f"Gathering conversation history for export...")

    # Ensure master history is up to date first
    trigger_history_merge()

    conv_dbs = glob.glob(os.path.join(MASTER_GEMINI, "conversations", "*.db"))
    brain_dirs = glob.glob(os.path.join(MASTER_GEMINI, "brain", "*"))

    log_info(f"Found {len(conv_dbs)} conversations and {len(brain_dirs)} brain artifact folders.")

    manifest = {
        "export_type": "history",
        "format_version": "1.0",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hostname": os.uname().nodename,
        "conversations_count": len(conv_dbs),
        "brain_folders_count": len(brain_dirs)
    }

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_p = os.path.join(tmpdir, "manifest.json")
        with open(manifest_p, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        mode = "w:gz" if output_path.endswith(".gz") else "w"
        with tarfile.open(output_path, mode) as tar:
            tar.add(manifest_p, arcname="manifest.json")

            conv_p = os.path.join(MASTER_GEMINI, "conversations")
            if os.path.isdir(conv_p):
                tar.add(conv_p, arcname="conversations", recursive=True)

            brain_p = os.path.join(MASTER_GEMINI, "brain")
            if os.path.isdir(brain_p):
                tar.add(brain_p, arcname="brain", recursive=True)

            anno_p = os.path.join(MASTER_GEMINI, "annotations")
            if os.path.isdir(anno_p):
                tar.add(anno_p, arcname="annotations", recursive=True)

            for sum_f in glob.glob(os.path.join(MASTER_GEMINI, "*summaries*")):
                if os.path.isfile(sum_f):
                    tar.add(sum_f, arcname=os.path.basename(sum_f))

    size_str = format_size(os.path.getsize(output_path))
    log_success(f"History export package created successfully!")
    print(f"  • Destination Archive: {BOLD}{output_path}{NC} ({size_str})")
    print(f"  • Total Conversations: {len(conv_dbs)}")
    print(f"  • Total Brain Folders: {len(brain_dirs)}")
    return output_path

def add_path_safe(tar, src_path, arc_prefix, visited=None):
    if visited is None:
        visited = set()
    if os.path.islink(src_path):
        if not os.path.exists(src_path):
            return
        real_p = os.path.realpath(src_path)
        if real_p in visited:
            return
        visited.add(real_p)
        if os.path.isdir(real_p):
            add_path_safe(tar, real_p, arc_prefix, visited)
            return
        elif os.path.isfile(real_p):
            try:
                ti = tar.gettarinfo(real_p, arcname=arc_prefix)
                with open(real_p, 'rb') as f:
                    tar.addfile(ti, f)
            except Exception:
                pass
            return

    if os.path.isfile(src_path):
        try:
            ti = tar.gettarinfo(src_path, arcname=arc_prefix)
            with open(src_path, 'rb') as f:
                tar.addfile(ti, f)
        except Exception:
            pass
        return

    if os.path.isdir(src_path):
        real_d = os.path.realpath(src_path)
        if real_d in visited:
            return
        visited.add(real_d)
        try:
            ti = tar.gettarinfo(src_path, arcname=arc_prefix)
            tar.addfile(ti)
        except Exception:
            pass
        try:
            entries = sorted(os.listdir(src_path))
        except Exception:
            return
        for item in entries:
            s_item = os.path.join(src_path, item)
            a_item = os.path.join(arc_prefix, item)
            add_path_safe(tar, s_item, a_item, visited)

def export_suite(output_path=None):
    """Exports rules, skills, plugins, MCP servers, and accounts/tokens."""
    if not output_path:
        ts = get_timestamp()
        output_path = os.path.join(REAL_HOME, f"antigravity-suite-export-{ts}.tar.gz")

    output_path = os.path.abspath(os.path.expanduser(output_path))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    log_info("Gathering suite configurations, rules, skills, and accounts...")

    skills_list = [d for d in glob.glob(os.path.join(CONFIG_DIR, "skills", "*")) if os.path.isdir(d)]
    mcp_list = [d for d in glob.glob(os.path.join(MASTER_GEMINI, "mcp", "*")) if os.path.isdir(d)]
    accounts_list = glob.glob(os.path.join(ANTIGRAVITY_CONF_DIR, "accounts", "*.json"))

    manifest = {
        "export_type": "suite",
        "format_version": "1.0",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hostname": os.uname().nodename,
        "skills_count": len(skills_list),
        "mcp_count": len(mcp_list),
        "accounts_count": len(accounts_list)
    }

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_p = os.path.join(tmpdir, "manifest.json")
        with open(manifest_p, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        mode = "w:gz" if output_path.endswith(".gz") else "w"
        with tarfile.open(output_path, mode) as tar:
            tar.add(manifest_p, arcname="manifest.json")

            # 1. Global Rules
            gemini_md = os.path.join(GEMINI_DIR, "GEMINI.md")
            if os.path.isfile(gemini_md):
                add_path_safe(tar, gemini_md, "GEMINI.md")

            # 2. Configs & Plugins
            for cf in ["config.json", "mcp_config.json"]:
                p = os.path.join(CONFIG_DIR, cf)
                if os.path.isfile(p):
                    add_path_safe(tar, p, os.path.join("config", cf))

            plugins_dir = os.path.join(CONFIG_DIR, "plugins")
            if os.path.isdir(plugins_dir):
                add_path_safe(tar, plugins_dir, "config/plugins")

            # 3. Skills (dereferenced safely, ignoring broken links)
            skills_dir = os.path.join(CONFIG_DIR, "skills")
            if os.path.isdir(skills_dir):
                add_path_safe(tar, skills_dir, "config/skills")

            # 4. Underlying .agents repository (if present)
            if os.path.isdir(AGENTS_DIR):
                add_path_safe(tar, AGENTS_DIR, "agents")

            # 5. MCP server definitions & tool wrappers
            mcp_dir = os.path.join(MASTER_GEMINI, "mcp")
            if os.path.isdir(mcp_dir):
                add_path_safe(tar, mcp_dir, "mcp")

            # 6. Accounts, Conf files, and tokens
            if os.path.isdir(ANTIGRAVITY_CONF_DIR):
                for conf_f in glob.glob(os.path.join(ANTIGRAVITY_CONF_DIR, "*.conf")):
                    add_path_safe(tar, conf_f, os.path.join("config_antigravity", os.path.basename(conf_f)))
                accs_dir = os.path.join(ANTIGRAVITY_CONF_DIR, "accounts")
                if os.path.isdir(accs_dir):
                    add_path_safe(tar, accs_dir, "accounts")

            token_targets = [
                (os.path.join(GEMINI_DIR, "jetski-standalone-oauth-token"), "gemini-token"),
                (os.path.join(REAL_HOME, ".antigravity-profile2", ".gemini", "jetski-standalone-oauth-token"), "acc2-token"),
                (os.path.join(REAL_HOME, ".gemini-ide", "jetski-standalone-oauth-token"), "gemini-ide-token"),
                (os.path.join(REAL_HOME, ".gemide", "jetski-standalone-oauth-token"), "gemide-token"),
            ]
            for token_path, token_arc in token_targets:
                if os.path.isfile(token_path):
                    add_path_safe(tar, token_path, os.path.join("tokens", token_arc))

    size_str = format_size(os.path.getsize(output_path))
    log_success(f"Suite configurations export package created successfully!")
    print(f"  • Destination Archive: {BOLD}{output_path}{NC} ({size_str})")
    print(f"  • Exported Skills:     {len(skills_list)}")
    print(f"  • Exported MCP Tools:  {len(mcp_list)}")
    print(f"  • Exported Accounts:   {len(accounts_list)}")
    return output_path

def export_all(output_path=None):
    """Exports both History AND Suite configurations in a single unified archive."""
    if not output_path:
        ts = get_timestamp()
        output_path = os.path.join(REAL_HOME, f"antigravity-full-backup-{ts}.tar.gz")

    output_path = os.path.abspath(os.path.expanduser(output_path))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    log_info("Creating full unified export package (History + Suite Configs)...")

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        hist_tar = os.path.join(tmpdir, "history_part.tar")
        suite_tar = os.path.join(tmpdir, "suite_part.tar")

        export_history(hist_tar)
        export_suite(suite_tar)

        manifest = {
            "export_type": "all",
            "format_version": "1.0",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "hostname": os.uname().nodename,
            "components": ["history", "suite"]
        }

        manifest_p = os.path.join(tmpdir, "manifest.json")
        with open(manifest_p, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        with tarfile.open(output_path, "w:gz") as final_tar:
            final_tar.add(manifest_p, arcname="manifest.json")
            added_names = {"manifest.json"}
            with tarfile.open(hist_tar, "r:") as h_tar:
                for member in h_tar.getmembers():
                    if member.name not in added_names:
                        f = h_tar.extractfile(member) if member.isreg() else None
                        final_tar.addfile(member, f)
                        added_names.add(member.name)
            with tarfile.open(suite_tar, "r:") as s_tar:
                for member in s_tar.getmembers():
                    if member.name not in added_names:
                        f = s_tar.extractfile(member) if member.isreg() else None
                        final_tar.addfile(member, f)
                        added_names.add(member.name)

    size_str = format_size(os.path.getsize(output_path))
    log_success(f"Full migration bundle created: {BOLD}{output_path}{NC} ({size_str})")
    return output_path

# ==============================================================================
# Import Functions
def trigger_history_merge():
    """Runs antigravity-merge-history.py to update indexes and IDE state."""
    if not MASTER_GEMINI or not os.path.exists(MASTER_GEMINI):
        return
    if os.environ.get("ANTIGRAVITY_TEST_MODE") == "1" or os.environ.get("ANTIGRAVITY_SKIP_SAFETY_BACKUP") == "1":
        return

    merge_script = os.path.join(LOCAL_BIN, "antigravity-merge-history.py")
    if not os.path.isfile(merge_script):
        # Fallback to repo bin
        merge_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antigravity-merge-history.py")

    if os.path.isfile(merge_script):
        try:
            subprocess.run([sys.executable, merge_script, "--master", MASTER_GEMINI, "--quiet"], check=False)
        except Exception as e:
            log_warn(f"Merge history trigger returned: {e}")

def import_history(archive_path=None, extracted_dir=None):
    """Imports and merges conversation history from an archive into the master pool."""
    if not extracted_dir and (not archive_path or not os.path.isfile(archive_path)):
        log_err(f"Archive file not found: {archive_path}")
        return False

    source_label = archive_path if archive_path else extracted_dir
    log_info(f"Importing conversation history from {source_label}...")

    # 1. Automatic safety backup before modifying local state
    create_safety_backup(category="history", label="pre_import")

    master_conv = os.path.join(MASTER_GEMINI, "conversations")
    master_brain = os.path.join(MASTER_GEMINI, "brain")
    master_anno = os.path.join(MASTER_GEMINI, "annotations")
    os.makedirs(master_conv, exist_ok=True)
    os.makedirs(master_brain, exist_ok=True)
    os.makedirs(master_anno, exist_ok=True)

    imported_dbs = 0
    imported_brains = 0

    import contextlib

    @contextlib.contextmanager
    def resolve_source():
        if extracted_dir:
            yield extracted_dir
        else:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                with tarfile.open(archive_path, "r:*") as tar:
                    safe_extract_tar(tar, path=tmp)
                yield tmp

    with resolve_source() as tmpdir:

        # Look for conversations folder
        src_conv = os.path.join(tmpdir, "conversations")
        if not os.path.isdir(src_conv):
            src_conv = os.path.join(tmpdir, "history", "conversations")

        if os.path.isdir(src_conv):
            for db in glob.glob(os.path.join(src_conv, "*.db")):
                fname = os.path.basename(db)
                dst = os.path.join(master_conv, fname)
                should_copy = False
                if not os.path.exists(dst):
                    should_copy = True
                else:
                    db_steps = get_db_step_count(db)
                    dst_steps = get_db_step_count(dst)
                    if db_steps > dst_steps:
                        should_copy = True
                    elif db_steps == dst_steps and os.path.getmtime(db) > os.path.getmtime(dst):
                        should_copy = True

                if should_copy:
                    shutil.copy2(db, dst)
                    for ext in ["-wal", "-shm"]:
                        s_wal = f"{db}{ext}"
                        d_wal = f"{dst}{ext}"
                        if os.path.exists(s_wal):
                            shutil.copy2(s_wal, d_wal)
                        elif os.path.exists(d_wal):
                            try: os.remove(d_wal)
                            except Exception: pass
                    imported_dbs += 1

        # Look for brain folder
        src_brain = os.path.join(tmpdir, "brain")
        if not os.path.isdir(src_brain):
            src_brain = os.path.join(tmpdir, "history", "brain")

        if os.path.isdir(src_brain):
            for b_item in glob.glob(os.path.join(src_brain, "*")):
                b_name = os.path.basename(b_item)
                dst_b = os.path.join(master_brain, b_name)
                if os.path.isdir(b_item):
                    shutil.copytree(b_item, dst_b, dirs_exist_ok=True)
                    imported_brains += 1
                else:
                    shutil.copy2(b_item, dst_b)
                    imported_brains += 1

        # Look for annotations folder
        src_anno = os.path.join(tmpdir, "annotations")
        if not os.path.isdir(src_anno):
            src_anno = os.path.join(tmpdir, "history", "annotations")

        if os.path.isdir(src_anno):
            for a_item in glob.glob(os.path.join(src_anno, "*")):
                dst_a = os.path.join(master_anno, os.path.basename(a_item))
                if not os.path.exists(dst_a):
                    shutil.copy2(a_item, dst_a)

    log_info(f"Ingested {imported_dbs} conversations and {imported_brains} brain folders.")
    log_info("Rebuilding conversation indexes, proto summaries, and IDE state...")
    trigger_history_merge()

    total_convs = len(glob.glob(os.path.join(master_conv, "*.db")))
    log_success(f"History import complete! Master shared pool now has {total_convs} total conversations.")
    return True

def merge_mcp_configs(local_cfg_p, incoming_cfg_p):
    """Intelligently merges two mcp_config.json files without dropping local servers."""
    if not os.path.isfile(incoming_cfg_p):
        return
    if not os.path.isfile(local_cfg_p):
        shutil.copy2(incoming_cfg_p, local_cfg_p)
        return

    try:
        with open(local_cfg_p, "r", encoding="utf-8") as f:
            local_data = json.load(f)
        with open(incoming_cfg_p, "r", encoding="utf-8") as f:
            incoming_data = json.load(f)

        local_servers = local_data.get("mcpServers", {})
        incoming_servers = incoming_data.get("mcpServers", {})

        for s_name, s_conf in incoming_servers.items():
            if s_name not in local_servers:
                local_servers[s_name] = s_conf

        local_data["mcpServers"] = local_servers
        with open(local_cfg_p, "w", encoding="utf-8") as f:
            json.dump(local_data, f, indent=2)
    except Exception as e:
        log_warn(f"Failed to merge mcp_config.json: {e}")

def import_suite(archive_path=None, extracted_dir=None):
    """Imports and merges rules, skills, plugins, MCP servers, and accounts from an archive."""
    if not extracted_dir and (not archive_path or not os.path.isfile(archive_path)):
        log_err(f"Archive file not found: {archive_path}")
        return False

    source_label = archive_path if archive_path else extracted_dir
    log_info(f"Importing suite configurations from {source_label}...")

    # 1. Safety backup of existing configs
    create_safety_backup(category="suite", label="pre_import")

    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(os.path.join(CONFIG_DIR, "skills"), exist_ok=True)
    os.makedirs(os.path.join(CONFIG_DIR, "plugins"), exist_ok=True)
    os.makedirs(os.path.join(MASTER_GEMINI, "mcp"), exist_ok=True)
    os.makedirs(os.path.join(ANTIGRAVITY_CONF_DIR, "accounts"), exist_ok=True)

    imported_skills = 0
    imported_mcps = 0
    imported_accs = 0

    import contextlib

    @contextlib.contextmanager
    def resolve_source():
        if extracted_dir:
            yield extracted_dir
        else:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                with tarfile.open(archive_path, "r:*") as tar:
                    safe_extract_tar(tar, path=tmp)
                yield tmp

    with resolve_source() as tmpdir:
        # 1. Global Rules (GEMINI.md)
        gemini_md_src = os.path.join(tmpdir, "GEMINI.md")
        if not os.path.isfile(gemini_md_src):
            gemini_md_src = os.path.join(tmpdir, "suite", "GEMINI.md")

        if os.path.isfile(gemini_md_src):
            dst_md = os.path.join(GEMINI_DIR, "GEMINI.md")
            shutil.copy2(gemini_md_src, dst_md)
            log_success("Restored global rules to ~/.gemini/GEMINI.md")

        # 2. Config & Plugins
        cfg_src = os.path.join(tmpdir, "config")
        if not os.path.isdir(cfg_src):
            cfg_src = os.path.join(tmpdir, "suite", "config")

        if os.path.isdir(cfg_src):
            # Restore config.json if present
            inc_cfg_json = os.path.join(cfg_src, "config.json")
            if os.path.isfile(inc_cfg_json):
                shutil.copy2(inc_cfg_json, os.path.join(CONFIG_DIR, "config.json"))

            # Intelligent merge for mcp_config.json
            inc_mcp_cfg = os.path.join(cfg_src, "mcp_config.json")
            merge_mcp_configs(os.path.join(CONFIG_DIR, "mcp_config.json"), inc_mcp_cfg)

            # Plugins
            inc_plugins = os.path.join(cfg_src, "plugins")
            if os.path.isdir(inc_plugins):
                for p_item in glob.glob(os.path.join(inc_plugins, "*")):
                    p_dst = os.path.join(CONFIG_DIR, "plugins", os.path.basename(p_item))
                    if os.path.isdir(p_item):
                        shutil.copytree(p_item, p_dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(p_item, p_dst)

            # Skills
            inc_skills = os.path.join(cfg_src, "skills")
            if os.path.isdir(inc_skills):
                for s_item in glob.glob(os.path.join(inc_skills, "*")):
                    s_name = os.path.basename(s_item)
                    s_dst = os.path.join(CONFIG_DIR, "skills", s_name)
                    if os.path.isdir(s_item):
                        shutil.copytree(s_item, s_dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s_item, s_dst)
                    imported_skills += 1

        # 3. Agents repository (if present)
        agents_src = os.path.join(tmpdir, "agents")
        if not os.path.isdir(agents_src):
            agents_src = os.path.join(tmpdir, "suite", "agents")
        if os.path.isdir(agents_src):
            os.makedirs(AGENTS_DIR, exist_ok=True)
            for a_item in glob.glob(os.path.join(agents_src, "*")):
                a_dst = os.path.join(AGENTS_DIR, os.path.basename(a_item))
                if os.path.isdir(a_item):
                    shutil.copytree(a_item, a_dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(a_item, a_dst)

        # 4. MCP Servers
        mcp_src = os.path.join(tmpdir, "mcp")
        if not os.path.isdir(mcp_src):
            mcp_src = os.path.join(tmpdir, "suite", "mcp")
        if os.path.isdir(mcp_src):
            for m_item in glob.glob(os.path.join(mcp_src, "*")):
                m_name = os.path.basename(m_item)
                m_dst = os.path.join(MASTER_GEMINI, "mcp", m_name)
                if os.path.isdir(m_item):
                    shutil.copytree(m_item, m_dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(m_item, m_dst)
                imported_mcps += 1

        # 5. Accounts & Configs
        accs_src = os.path.join(tmpdir, "accounts")
        if not os.path.isdir(accs_src):
            accs_src = os.path.join(tmpdir, "suite", "accounts")
        if os.path.isdir(accs_src):
            for acc_f in glob.glob(os.path.join(accs_src, "*.json")):
                acc_dst = os.path.join(ANTIGRAVITY_CONF_DIR, "accounts", os.path.basename(acc_f))
                shutil.copy2(acc_f, acc_dst)
                imported_accs += 1

        confs_src = os.path.join(tmpdir, "config_antigravity")
        if not os.path.isdir(confs_src):
            confs_src = os.path.join(tmpdir, "suite", "config_antigravity")
        if os.path.isdir(confs_src):
            for cf in glob.glob(os.path.join(confs_src, "*.conf")):
                c_dst = os.path.join(ANTIGRAVITY_CONF_DIR, os.path.basename(cf))
                shutil.copy2(cf, c_dst)

        # 6. OAuth Tokens
        tokens_src = os.path.join(tmpdir, "tokens")
        if not os.path.isdir(tokens_src):
            tokens_src = os.path.join(tmpdir, "suite", "tokens")
        if os.path.isdir(tokens_src):
            token_restore_map = [
                ("gemini-token", os.path.join(GEMINI_DIR, "jetski-standalone-oauth-token")),
                (".gemini-token", os.path.join(GEMINI_DIR, "jetski-standalone-oauth-token")),
                ("acc2-token", os.path.join(REAL_HOME, ".antigravity-profile2", ".gemini", "jetski-standalone-oauth-token")),
                ("gemini-ide-token", os.path.join(REAL_HOME, ".gemini-ide", "jetski-standalone-oauth-token")),
                (".gemini-ide-token", os.path.join(REAL_HOME, ".gemini-ide", "jetski-standalone-oauth-token")),
                ("gemide-token", os.path.join(REAL_HOME, ".gemide", "jetski-standalone-oauth-token")),
                (".gemide-token", os.path.join(REAL_HOME, ".gemide", "jetski-standalone-oauth-token")),
            ]
            for src_name, dst_path in token_restore_map:
                token_src_file = os.path.join(tokens_src, src_name)
                if os.path.isfile(token_src_file):
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(token_src_file, dst_path)
                    try:
                        os.chmod(dst_path, 0o600)
                    except Exception:
                        pass
                    log_success(f"Restored OAuth token to {dst_path}")

    log_success("Suite configuration import completed successfully!")
    print(f"  • Imported Skills:   {imported_skills}")
    print(f"  • Imported MCPs:     {imported_mcps}")
    print(f"  • Imported Accounts: {imported_accs}")
    return True

def import_all(archive_path):
    """Automatically detects archive type and performs required import(s)."""
    if not os.path.isfile(archive_path):
        log_err(f"Archive file not found: {archive_path}")
        return False

    manifest = None
    try:
        with tarfile.open(archive_path, "r:*") as tar:
            try:
                mf = tar.extractfile("manifest.json")
                if mf:
                    manifest = json.load(mf)
            except KeyError:
                pass
    except Exception as e:
        log_err(f"Could not read archive: {e}")
        return False

    exp_type = manifest.get("export_type") if manifest else None

    # Fallback heuristic if no manifest
    if not exp_type:
        fn = os.path.basename(archive_path).lower()
        if "history" in fn:
            exp_type = "history"
        elif "suite" in fn:
            exp_type = "suite"
        else:
            exp_type = "all"

    log_info(f"Archive detected as type: {BOLD}{exp_type.upper()}{NC}")

    if exp_type == "history":
        return import_history(archive_path=archive_path)
    elif exp_type == "suite":
        return import_suite(archive_path=archive_path)
    elif exp_type in ["all", "full"]:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(archive_path, "r:*") as tar:
                safe_extract_tar(tar, path=tmpdir)
            h_ok = import_history(extracted_dir=tmpdir)
            s_ok = import_suite(extracted_dir=tmpdir)
            return h_ok and s_ok
    else:
        log_err(f"Unknown archive export_type: {exp_type}")
        return False

# ==============================================================================
# CLI Entry Point
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Antigravity Suite Cross-System Migration & Backup Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # export-history
    p_ex_h = subparsers.add_parser("export-history", help="Export conversation history to tarball")
    p_ex_h.add_argument("output", nargs="?", default=None, help="Output tarball path")

    # import-history
    p_im_h = subparsers.add_parser("import-history", help="Import conversation history from tarball")
    p_im_h.add_argument("archive", help="Path to archive tarball")

    # export-suite
    p_ex_s = subparsers.add_parser("export-suite", help="Export suite configs, rules, skills, MCP, accounts")
    p_ex_s.add_argument("output", nargs="?", default=None, help="Output tarball path")

    # import-suite
    p_im_s = subparsers.add_parser("import-suite", help="Import suite configs, rules, skills, MCP, accounts")
    p_im_s.add_argument("archive", help="Path to archive tarball")

    # export-all
    p_ex_a = subparsers.add_parser("export-all", help="Export both history and suite configs")
    p_ex_a.add_argument("output", nargs="?", default=None, help="Output tarball path")

    # import-all
    p_im_a = subparsers.add_parser("import-all", help="Auto-detect and import archive")
    p_im_a.add_argument("archive", help="Path to archive tarball")

    # backups
    p_bks = subparsers.add_parser("list-backups", help="List available local snapshots and backups")

    p_cr_b = subparsers.add_parser("create-backup", help="Create an instant safety snapshot")
    p_cr_b.add_argument("--category", default="all", choices=["history", "suite", "all"], help="Snapshot category")
    p_cr_b.add_argument("--label", default="manual", help="Snapshot label")

    p_rst = subparsers.add_parser("restore-backup", help="Restore state from a local backup archive")
    p_rst.add_argument("backup_path", help="Path to backup tarball")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "export-history":
        export_history(args.output)
    elif args.command == "import-history":
        import_history(args.archive)
    elif args.command == "export-suite":
        export_suite(args.output)
    elif args.command == "import-suite":
        import_suite(args.archive)
    elif args.command == "export-all":
        export_all(args.output)
    elif args.command == "import-all":
        import_all(args.archive)
    elif args.command == "list-backups":
        list_all_backups()
    elif args.command == "create-backup":
        create_safety_backup(category=args.category, label=args.label)
    elif args.command == "restore-backup":
        restore_backup(args.backup_path)

if __name__ == "__main__":
    main()
