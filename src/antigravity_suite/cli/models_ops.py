"""CLI operations for custom model providers, discovery, and selection."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from antigravity_suite.models.config import load_config, save_config
from antigravity_suite.models.discovery import fetch_models
from antigravity_suite.models.parser import parse_model_catalog
from antigravity_suite.models.selector import enable_all_models, enable_selected_models

G, R, C, Y, BOLD, NC = "\033[0;32m", "\033[0;31m", "\033[0;36m", "\033[0;33m", "\033[1m", "\033[0m"


def _get_providers_list(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    p = cfg.get("providers", {})
    if isinstance(p, dict):
        return [{"id": k, **v} if isinstance(v, dict) else {"id": k, "name": k} for k, v in p.items()]
    return [x for x in p if isinstance(x, dict)]


def op_list() -> int:
    cfg = load_config()
    provs = _get_providers_list(cfg)
    models = cfg.get("models", [])
    print(f"\n{C}{'=' * 75}{NC}")
    print(f"{BOLD}{C}         Antigravity Custom Providers & Configured Models          {NC}")
    print(f"{C}{'=' * 75}{NC}")
    print(f"{BOLD}{'Provider Name':<20} {'Base URL':<35} {'Auth':<10} {'Status'}{NC}")
    print("-" * 75)
    for p in provs:
        auth_tag = f"{G}Token{NC}" if p.get("api_key") or p.get("apiKey") else f"{Y}None{NC}"
        st_tag = f"{G}Active{NC}" if p.get("enabled", True) else f"{R}Disabled{NC}"
        print(f"  {p.get('name', p.get('id', 'custom')):<18} {p.get('base_url', p.get('apiUrl', '')):<33} {auth_tag:<19} {st_tag}")
    print(f"\n{BOLD}Active / Registered Models ({len(models)}):{NC}")
    print("-" * 75)
    for m in models:
        st = f"{G}[ON]{NC}" if m.get("enabled", True) else f"{R}[OFF]{NC}"
        ctx = f"{m.get('context_length') // 1024}k" if m.get("context_length") else "N/A"
        name = m.get("displayName") or m.get("name") or m.get("id", "")
        print(f"  {st} {name:<40} (Ctx: {ctx}, Prov: {m.get('provider', 'custom')})")
    print(f"{C}{'=' * 75}{NC}\n")
    return 0


def op_add_provider(name: str, url: str, token: Optional[str] = None) -> int:
    cfg = load_config()
    clean_id = name.lower().replace(" ", "-").replace("/", "-")
    entry = {"name": name, "base_url": url, "apiUrl": url, "enabled": True}
    if token:
        entry["api_key"] = token
        entry["apiKey"] = token
    if isinstance(cfg.get("providers"), dict):
        cfg["providers"][clean_id] = entry
    else:
        provs = [p for p in _get_providers_list(cfg) if p.get("id") != clean_id]
        provs.append({"id": clean_id, **entry})
        cfg["providers"] = provs
    save_config(cfg)
    print(f"{G}[SUCCESS]{NC} Registered provider: {BOLD}{name}{NC} ({url})")
    return 0


def op_fetch(provider: str) -> int:
    cfg = load_config()
    provs = _get_providers_list(cfg)
    p = next((x for x in provs if x.get("id") == provider.lower() or x.get("name") == provider), None)
    if not p:
        print(f"{R}[ERROR]{NC} Provider '{provider}' not found.")
        return 1
    url = p.get("base_url") or p.get("apiUrl", "")
    token = p.get("api_key") or p.get("apiKey")
    print(f"Fetching models from {BOLD}{url}{NC}...")
    try:
        raw = fetch_models(url, api_key=token)
        catalog = parse_model_catalog(raw)
        print(f"{G}[SUCCESS]{NC} Discovered {len(catalog)} models from {BOLD}{p.get('name')}{NC}:")
        for idx, m in enumerate(catalog[:30], 1):
            vis = f"{G}Vision{NC}" if m.capabilities.get("vision") else ""
            think = f"{C}Thinking{NC}" if m.capabilities.get("thinking") else ""
            feats = " ".join(filter(None, [vis, think]))
            print(f"  [{idx:2d}] {m.id:<38} {feats}")
        if len(catalog) > 30:
            print(f"  ... and {len(catalog) - 30} more models available.")
        return 0
    except Exception as e:
        print(f"{R}[ERROR]{NC} Discovery failed: {e}")
        return 1
