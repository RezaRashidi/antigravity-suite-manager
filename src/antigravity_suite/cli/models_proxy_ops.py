"""CLI operations for local model proxy and Antigravity IDE configuration."""

from __future__ import annotations

import os
import subprocess
from antigravity_suite.cli.models_ops import _get_providers_list
from antigravity_suite.models.config import load_config, save_config
from antigravity_suite.models.discovery import fetch_models
from antigravity_suite.models.ide_adapter import apply_ide_proxy_url, restore_ide_proxy_url
from antigravity_suite.models.parser import parse_model_catalog
from antigravity_suite.models.proxy_daemon import get_proxy_status, start_proxy_daemon, stop_proxy_daemon
from antigravity_suite.models.selector import enable_all_models, enable_selected_models
from antigravity_suite.models.tester import test_model_endpoint

G, R, C, Y, BOLD, NC = "\033[0;32m", "\033[0;31m", "\033[0;36m", "\033[0;33m", "\033[1m", "\033[0m"


def op_enable_all(provider: str) -> int:
    cfg = load_config()
    p = next((x for x in _get_providers_list(cfg) if x.get("id") == provider.lower() or x.get("name") == provider), None)
    if not p:
        print(f"{R}[ERROR]{NC} Provider '{provider}' not found.")
        return 1
    raw = fetch_models(p.get("base_url") or p.get("apiUrl", ""), api_key=p.get("api_key"))
    catalog = parse_model_catalog(raw)
    cfg = enable_all_models(cfg, p.get("id", provider), catalog)
    save_config(cfg)
    print(f"{G}[SUCCESS]{NC} Enabled all {len(catalog)} models from {BOLD}{p.get('name')}{NC}.")
    return 0


def op_select(provider: str, model_ids: list[str]) -> int:
    cfg = load_config()
    p = next((x for x in _get_providers_list(cfg) if x.get("id") == provider.lower() or x.get("name") == provider), None)
    if not p:
        print(f"{R}[ERROR]{NC} Provider '{provider}' not found.")
        return 1
    raw = fetch_models(p.get("base_url") or p.get("apiUrl", ""), api_key=p.get("api_key"))
    catalog = parse_model_catalog(raw)
    cfg = enable_selected_models(cfg, p.get("id", provider), catalog, model_ids)
    save_config(cfg)
    print(f"{G}[SUCCESS]{NC} Activated {len(model_ids)} selected models for {BOLD}{p.get('name')}{NC}.")
    return 0


def op_test(provider: str, model_id: str) -> int:
    cfg = load_config()
    p = next((x for x in _get_providers_list(cfg) if x.get("id") == provider.lower() or x.get("name") == provider), None)
    url = p.get("base_url") if p else provider
    token = p.get("api_key") if p else None
    print(f"Testing {BOLD}{model_id}{NC} on {BOLD}{url}{NC}...")
    ok, lat, reply = test_model_endpoint(url, model_id, api_key=token)
    if ok:
        print(f"{G}[SUCCESS]{NC} Latency: {BOLD}{lat} ms{NC} | Response: {reply[:60]}")
        return 0
    print(f"{R}[FAILURE]{NC} Error: {reply}")
    return 1


def op_proxy(action: str) -> int:
    if action == "proxy-start":
        ok = start_proxy_daemon()
        st = get_proxy_status()
        print(f"{G}[SUCCESS]{NC} Proxy daemon started on port {st['port']} (PID {st['pid']})" if ok else f"{R}[ERROR]{NC} Failed to start.")
        return 0 if ok else 1
    if action == "proxy-stop":
        ok = stop_proxy_daemon()
        print(f"{G}[SUCCESS]{NC} Proxy daemon stopped." if ok else f"{Y}[INFO]{NC} Proxy was not running.")
        return 0
    st = get_proxy_status()
    st_tag = f"{G}Running{NC} (PID {st['pid']})" if st["running"] else f"{R}Stopped{NC}"
    print(f"Model Proxy Status: {st_tag} on port {st['port']}")
    return 0


def op_ide(action: str) -> int:
    if action == "apply-ide":
        p = apply_ide_proxy_url()
        print(f"{G}[SUCCESS]{NC} Applied custom model proxy to Antigravity IDE: {p}")
        return 0
    p = restore_ide_proxy_url()
    print(f"{G}[SUCCESS]{NC} Restored official Google Gemini settings for IDE: {p}")
    return 0
