"""
Intelligent merge utility for mcp_config.json files.
"""

from __future__ import annotations

import json
import os
from antigravity_suite.migration.constants import log_info, log_warn


def merge_mcp_configs(local_cfg_p: str, incoming_cfg_p: str) -> None:
    """Intelligently merges two mcp_config.json files without dropping local servers."""
    if not os.path.isfile(incoming_cfg_p):
        return
    if not os.path.isfile(local_cfg_p):
        import shutil
        shutil.copy2(incoming_cfg_p, local_cfg_p)
        return

    try:
        with open(local_cfg_p, "r", encoding="utf-8") as f: local_data = json.load(f)
        with open(incoming_cfg_p, "r", encoding="utf-8") as f: inc_data = json.load(f)

        local_servers = local_data.setdefault("mcpServers", {})
        inc_servers = inc_data.get("mcpServers", {})
        merged_count = 0
        for s_name, s_cfg in inc_servers.items():
            if s_name not in local_servers:
                local_servers[s_name] = s_cfg
                merged_count += 1

        with open(local_cfg_p, "w", encoding="utf-8") as f:
            json.dump(local_data, f, indent=2)
        if merged_count:
            log_info(f"Merged {merged_count} new MCP servers into local mcp_config.json")
    except Exception as e:
        log_warn(f"Failed to merge mcp_config.json: {e}")
