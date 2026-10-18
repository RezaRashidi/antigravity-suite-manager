"""
Suite configuration, skills, MCP, accounts, and tokens import engine.
"""

from __future__ import annotations

import contextlib
import glob
import os
import shutil
import tarfile
import tempfile
from antigravity_suite.migration.constants import (
    AGENTS_DIR,
    ANTIGRAVITY_CONF_DIR,
    CONFIG_DIR,
    GEMINI_DIR,
    MASTER_GEMINI,
    REAL_HOME,
    log_err,
    log_info,
    log_success,
)
from antigravity_suite.migration.mcp_merge import merge_mcp_configs
from antigravity_suite.migration.safety import create_safety_backup
from antigravity_suite.migration.tar_utils import safe_extract_tar


def import_suite(archive_path: str | None = None, extracted_dir: str | None = None) -> bool:
    """Imports and merges rules, skills, plugins, MCP servers, and accounts from an archive."""
    if not extracted_dir and (not archive_path or not os.path.isfile(archive_path)):
        log_err(f"Archive file not found: {archive_path}")
        return False

    log_info(f"Importing suite configurations from {archive_path or extracted_dir}...")
    create_safety_backup(category="suite", label="pre_import")

    for d in [CONFIG_DIR, os.path.join(CONFIG_DIR, "skills"), os.path.join(CONFIG_DIR, "plugins"), os.path.join(MASTER_GEMINI, "mcp"), os.path.join(ANTIGRAVITY_CONF_DIR, "accounts")]:
        os.makedirs(d, exist_ok=True)

    @contextlib.contextmanager
    def _res():
        if extracted_dir: yield extracted_dir
        else:
            with tempfile.TemporaryDirectory() as tmp:
                with tarfile.open(archive_path, "r:*") as tar: safe_extract_tar(tar, path=tmp)
                yield tmp

    with _res() as tmpdir:
        g_md = os.path.join(tmpdir, "GEMINI.md") if os.path.isfile(os.path.join(tmpdir, "GEMINI.md")) else os.path.join(tmpdir, "suite", "GEMINI.md")
        if os.path.isfile(g_md): shutil.copy2(g_md, os.path.join(GEMINI_DIR, "GEMINI.md"))

        cfg_s = os.path.join(tmpdir, "config") if os.path.isdir(os.path.join(tmpdir, "config")) else os.path.join(tmpdir, "suite", "config")
        if os.path.isdir(cfg_s):
            if os.path.isfile(os.path.join(cfg_s, "config.json")): shutil.copy2(os.path.join(cfg_s, "config.json"), os.path.join(CONFIG_DIR, "config.json"))
            merge_mcp_configs(os.path.join(CONFIG_DIR, "mcp_config.json"), os.path.join(cfg_s, "mcp_config.json"))
            for sub in ["plugins", "skills"]:
                if os.path.isdir(os.path.join(cfg_s, sub)): shutil.copytree(os.path.join(cfg_s, sub), os.path.join(CONFIG_DIR, sub), dirs_exist_ok=True)

        for src_name, dst_dir in [("agents", AGENTS_DIR), ("mcp", os.path.join(MASTER_GEMINI, "mcp")), ("accounts", os.path.join(ANTIGRAVITY_CONF_DIR, "accounts"))]:
            p = os.path.join(tmpdir, src_name) if os.path.isdir(os.path.join(tmpdir, src_name)) else os.path.join(tmpdir, "suite", src_name)
            if os.path.isdir(p): shutil.copytree(p, dst_dir, dirs_exist_ok=True)

        conf_s = os.path.join(tmpdir, "config_antigravity") if os.path.isdir(os.path.join(tmpdir, "config_antigravity")) else os.path.join(tmpdir, "suite", "config_antigravity")
        if os.path.isdir(conf_s):
            for cf in glob.glob(os.path.join(conf_s, "*.conf")): shutil.copy2(cf, os.path.join(ANTIGRAVITY_CONF_DIR, os.path.basename(cf)))

        tok_s = os.path.join(tmpdir, "tokens") if os.path.isdir(os.path.join(tmpdir, "tokens")) else os.path.join(tmpdir, "suite", "tokens")
        if os.path.isdir(tok_s):
            for sn, dp in [
                ("gemini-token", os.path.join(GEMINI_DIR, "jetski-standalone-oauth-token")),
                (".gemini-token", os.path.join(GEMINI_DIR, "jetski-standalone-oauth-token")),
                ("acc2-token", os.path.join(REAL_HOME, ".antigravity-profile2", ".gemini", "jetski-standalone-oauth-token")),
                ("gemini-ide-token", os.path.join(REAL_HOME, ".gemini-ide", "jetski-standalone-oauth-token")),
                (".gemini-ide-token", os.path.join(REAL_HOME, ".gemini-ide", "jetski-standalone-oauth-token")),
                ("gemide-token", os.path.join(REAL_HOME, ".gemide", "jetski-standalone-oauth-token")),
                (".gemide-token", os.path.join(REAL_HOME, ".gemide", "jetski-standalone-oauth-token")),
            ]:
                if os.path.isfile(os.path.join(tok_s, sn)):
                    os.makedirs(os.path.dirname(dp), exist_ok=True)
                    shutil.copy2(os.path.join(tok_s, sn), dp)
                    try: os.chmod(dp, 0o600)
                    except Exception: pass
                    log_success(f"Restored OAuth token to {dp}")

    log_success("Suite configuration import completed successfully!")
    return True
