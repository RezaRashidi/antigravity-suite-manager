"""
Context and prompt bloat inspector for MCP servers, tools, skills, and rules.
"""

from __future__ import annotations

import json
import os
from typing import List

from .models import ContextMetric

_MCP_CFG = os.path.expanduser("~/.gemini/config/mcp_config.json")
_MCP_DIR = os.path.expanduser("~/.gemini/antigravity/mcp")
_SKILLS_DIRS = [
    os.path.expanduser("~/.gemini/config/skills"),
    os.path.expanduser("~/.agents/skills"),
]
_RULES_DIRS = [
    os.path.expanduser("~/.agent/rules"),
    os.path.expanduser("~/.agents/rules"),
]


def count_mcp() -> tuple[int, int, int]:
    servers, eager_tools, lazy_tools = 0, 0, 0
    if os.path.isfile(_MCP_CFG):
        try:
            with open(_MCP_CFG, "r", encoding="utf-8") as f:
                data = json.load(f)
                srvs = data.get("mcpServers", {})
                servers = len(srvs)
        except Exception:
            pass

    if os.path.isdir(_MCP_DIR):
        for root, _, files in os.walk(_MCP_DIR):
            for file in files:
                if file.endswith(".json"):
                    lazy_tools += 1
    return servers, eager_tools, lazy_tools


def count_markdown_items(dirs: List[str], target_name: str | None = None) -> int:
    total = 0
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for entry in os.scandir(d):
            if entry.is_dir():
                if target_name and os.path.isfile(os.path.join(entry.path, target_name)):
                    total += 1
            elif entry.is_file() and entry.name.endswith(".md"):
                if not target_name:
                    total += 1
    return total


def benchmark_context() -> ContextMetric:
    metric = ContextMetric()
    metric.mcp_servers, metric.mcp_eager_tools, metric.mcp_lazy_tools = count_mcp()
    metric.total_mcp_tools = metric.mcp_eager_tools + metric.mcp_lazy_tools
    metric.active_skills = count_markdown_items(_SKILLS_DIRS, target_name="SKILL.md")
    metric.active_rules = count_markdown_items(_RULES_DIRS)

    tokens = (
        (metric.mcp_eager_tools * 220)
        + (metric.mcp_lazy_tools * 25)
        + (metric.active_skills * 140)
        + (metric.active_rules * 110)
        + 1200
    )
    metric.estimated_prompt_tokens = tokens
    return metric
