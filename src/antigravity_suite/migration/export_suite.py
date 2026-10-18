"""
Suite configurations, rules, skills, MCP, and accounts export engine.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import tarfile
import tempfile
from antigravity_suite.migration.constants import (
    AGENTS_DIR,
    ANTIGRAVITY_CONF_DIR,
    BOLD,
    CONFIG_DIR,
    GEMINI_DIR,
    MASTER_GEMINI,
    NC,
    REAL_HOME,
    log_info,
    log_success,
)
from antigravity_suite.migration.tar_utils import add_path_safe, format_size, get_timestamp


def export_suite(output_path: str | None = None) -> str:
    """Exports rules, skills, plugins, MCP servers, and accounts/tokens."""
    if not output_path:
        output_path = os.path.join(REAL_HOME, f"antigravity-suite-export-{get_timestamp()}.tar.gz")

    output_path = os.path.abspath(os.path.expanduser(output_path))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    log_info("Gathering suite configurations, rules, skills, and accounts...")

    skills_list = [d for d in glob.glob(os.path.join(CONFIG_DIR, "skills", "*")) if os.path.isdir(d)]
    mcp_list = [d for d in glob.glob(os.path.join(MASTER_GEMINI, "mcp", "*")) if os.path.isdir(d)]
    accounts_list = glob.glob(os.path.join(ANTIGRAVITY_CONF_DIR, "accounts", "*.json"))

    manifest = {
        "export_type": "suite", "format_version": "1.0",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hostname": os.uname().nodename,
        "skills_count": len(skills_list), "mcp_count": len(mcp_list), "accounts_count": len(accounts_list),
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        mf_p = os.path.join(tmpdir, "manifest.json")
        with open(mf_p, "w", encoding="utf-8") as f: json.dump(manifest, f, indent=2)

        mode = "w:gz" if output_path.endswith(".gz") else "w"
        with tarfile.open(output_path, mode) as tar:
            tar.add(mf_p, arcname="manifest.json")
            if os.path.isfile(os.path.join(GEMINI_DIR, "GEMINI.md")):
                add_path_safe(tar, os.path.join(GEMINI_DIR, "GEMINI.md"), "GEMINI.md")

            for cf in ["config.json", "mcp_config.json"]:
                p = os.path.join(CONFIG_DIR, cf)
                if os.path.isfile(p): add_path_safe(tar, p, os.path.join("config", cf))

            for sub, arc in [("plugins", "config/plugins"), ("skills", "config/skills")]:
                p = os.path.join(CONFIG_DIR, sub)
                if os.path.isdir(p): add_path_safe(tar, p, arc)

            if os.path.isdir(AGENTS_DIR): add_path_safe(tar, AGENTS_DIR, "agents")
            if os.path.isdir(os.path.join(MASTER_GEMINI, "mcp")):
                add_path_safe(tar, os.path.join(MASTER_GEMINI, "mcp"), "mcp")

            if os.path.isdir(ANTIGRAVITY_CONF_DIR):
                for conf_f in glob.glob(os.path.join(ANTIGRAVITY_CONF_DIR, "*.conf")):
                    add_path_safe(tar, conf_f, os.path.join("config_antigravity", os.path.basename(conf_f)))
                if os.path.isdir(os.path.join(ANTIGRAVITY_CONF_DIR, "accounts")):
                    add_path_safe(tar, os.path.join(ANTIGRAVITY_CONF_DIR, "accounts"), "accounts")

            token_targets = [
                (os.path.join(GEMINI_DIR, "jetski-standalone-oauth-token"), "gemini-token"),
                (os.path.join(REAL_HOME, ".antigravity-profile2", ".gemini", "jetski-standalone-oauth-token"), "acc2-token"),
                (os.path.join(REAL_HOME, ".gemini-ide", "jetski-standalone-oauth-token"), "gemini-ide-token"),
                (os.path.join(REAL_HOME, ".gemide", "jetski-standalone-oauth-token"), "gemide-token"),
            ]
            for tp, ta in token_targets:
                if os.path.isfile(tp): add_path_safe(tar, tp, os.path.join("tokens", ta))

    log_success(f"Suite configurations export package created successfully! ({format_size(os.path.getsize(output_path))})")
    print(f"  • Destination Archive: {BOLD}{output_path}{NC}\n  • Exported Skills: {len(skills_list)}\n  • Exported MCP Tools: {len(mcp_list)}\n  • Exported Accounts: {len(accounts_list)}")
    return output_path
