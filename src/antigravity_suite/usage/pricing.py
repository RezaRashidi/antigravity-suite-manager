"""
Model pricing registry backed by models.dev (24h local cache) with curated fallback rates.
Shared cache file (~/.config/antigravity/model_prices.json) is also readable by Node router.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from antigravity_suite.detect.constants import CONF_DIR

PRICES_URL = "https://models.dev/api.json"
CACHE_TTL_SEC = 24 * 3600
MAX_PRICE_PER_1M = 1000.0

# Curated fallback USD per 1M tokens + context window limits (tokens)
FALLBACK_RATES: Dict[str, Dict[str, Any]] = {
    "gemini-2.5-pro": {"name": "Gemini 2.5 Pro", "input": 1.25, "cache_read": 0.3125, "output": 10.0, "context_limit": 1_048_576},
    "gemini-2.5-flash": {"name": "Gemini 2.5 Flash", "input": 0.30, "cache_read": 0.075, "output": 2.50, "context_limit": 1_048_576},
    "gemini-2.5-flash-lite": {"name": "Gemini 2.5 Flash Lite", "input": 0.10, "cache_read": 0.025, "output": 0.40, "context_limit": 1_048_576},
    "gemini-3-pro": {"name": "Gemini 3 Pro", "input": 2.00, "cache_read": 0.20, "output": 12.0, "context_limit": 1_048_576},
    "gemini-3.5-flash": {"name": "Gemini 3.5 Flash", "input": 0.50, "cache_read": 0.05, "output": 3.00, "context_limit": 1_048_576},
    "gemini-3.8-flash": {"name": "Gemini 3.8 Flash", "input": 0.50, "cache_read": 0.05, "output": 3.00, "context_limit": 1_048_576},
    "gemini-4-carbon": {"name": "Gemini 4 Carbon", "input": 0.50, "cache_read": 0.05, "output": 3.00, "context_limit": 1_048_576},
    "gemini-4-hydrogen": {"name": "Gemini 4 Hydrogen", "input": 2.00, "cache_read": 0.20, "output": 12.0, "context_limit": 1_048_576},
    "gemini-4-neon": {"name": "Gemini 4 Neon", "input": 2.00, "cache_read": 0.20, "output": 12.0, "context_limit": 1_048_576},
    "claude-sonnet-4-5": {"name": "Claude Sonnet 4.5", "input": 3.00, "cache_read": 0.30, "output": 15.0, "context_limit": 200_000},
    "claude-sonnet-4-6": {"name": "Claude Sonnet 4.6", "input": 3.00, "cache_read": 0.30, "output": 15.0, "context_limit": 200_000},
    "claude-sonnet-5-5": {"name": "Claude Sonnet 5.5", "input": 3.00, "cache_read": 0.30, "output": 15.0, "context_limit": 200_000},
    "claude-opus-4-5": {"name": "Claude Opus 4.5", "input": 5.00, "cache_read": 0.50, "output": 25.0, "context_limit": 200_000},
    "claude-opus-4-6": {"name": "Claude Opus 4.6", "input": 5.00, "cache_read": 0.50, "output": 25.0, "context_limit": 200_000},
    "claude-haiku-4-5": {"name": "Claude Haiku 4.5", "input": 1.00, "cache_read": 0.10, "output": 5.0, "context_limit": 200_000},
    "gpt-oss-120b": {"name": "GPT OSS 120B", "input": 0.15, "cache_read": 0.15, "output": 0.60, "context_limit": 131_072},
}

_EFFORT_SUFFIX_RE = re.compile(r"(?:[-_](?:minimal|low|medium|high|xhigh|thinking|preview|latest)|@\d{8})$")
_KEY_RE = re.compile(r"[^a-z0-9.\-]+")


def get_prices_cache_file() -> Path:
    return Path(CONF_DIR) / "model_prices.json"


def _safe_num(val: Any) -> Optional[float]:
    if isinstance(val, (int, float)) and not isinstance(val, bool) and 0.0 <= float(val) <= MAX_PRICE_PER_1M:
        return float(val)
    return None


def _safe_int(val: Any, default: int = 1_048_576) -> int:
    if isinstance(val, (int, float)) and not isinstance(val, bool) and int(val) > 0:
        return int(val)
    return default


def normalize_model_key(model_name: str) -> str:
    """Normalizes internal Antigravity / Vertex / transcript model IDs for pricing lookup."""
    if not model_name:
        return "unknown"
    s = str(model_name).strip().lower()
    if "/" in s:
        s = s.rsplit("/", 1)[-1]
    for prefix in ("model_vertex_", "model_anthropic_", "model_openai_", "model_"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    s = s.replace("_", "-")
    s = _KEY_RE.sub("-", s).strip("-")
    while True:
        stripped = _EFFORT_SUFFIX_RE.sub("", s)
        if stripped == s:
            break
        s = stripped
    return s or "unknown"


def extract_models_dev_rates(raw_api: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extracts sanitized per-1M token rates from models.dev JSON across relevant providers."""
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(raw_api, dict):
        return out
    for provider in ("google-vertex", "google", "anthropic", "google-vertex-anthropic"):
        prov_obj = raw_api.get(provider)
        models = prov_obj.get("models") if isinstance(prov_obj, dict) else None
        if not isinstance(models, dict):
            continue
        for mid, info in models.items():
            if not isinstance(info, dict):
                continue
            cost = info.get("cost")
            if not isinstance(cost, dict):
                continue
            inp = _safe_num(cost.get("input"))
            outp = _safe_num(cost.get("output"))
            if inp is None or outp is None or (inp == 0.0 and outp == 0.0):
                continue
            cr = _safe_num(cost.get("cache_read"))
            limit = info.get("limit") if isinstance(info.get("limit"), dict) else {}
            ctx = _safe_int(limit.get("context"), 200_000 if "claude" in mid.lower() else 1_048_576)
            norm_id = normalize_model_key(mid)
            entry = {
                "name": str(info.get("name") or mid)[:80],
                "input": inp,
                "cache_read": cr if cr is not None else inp,
                "output": outp,
                "context_limit": ctx,
            }
            if norm_id not in out:
                out[norm_id] = entry
    return out


def fetch_models_dev_json(timeout: float = 4.0) -> Dict[str, Any]:
    req = urllib.request.Request(
        PRICES_URL,
        headers={"Accept": "application/json", "User-Agent": "antigravity-suite-manager"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(32 * 1024 * 1024)
    return json.loads(raw.decode("utf-8"))


def load_price_table(
    refresh: bool = False,
    timeout: float = 4.0,
    allow_network: bool = True,
    cache_file: Optional[Path] = None,
) -> Dict[str, Any]:
    """Loads cached models.dev pricing merged over offline fallbacks."""
    cf = cache_file or get_prices_cache_file()
    cached_models: Dict[str, Dict[str, Any]] = {}
    fetched_at: float = 0.0
    source = "fallback"

    if cf.is_file():
        try:
            saved = json.loads(cf.read_text(encoding="utf-8"))
            if isinstance(saved, dict) and isinstance(saved.get("models"), dict):
                cached_models = saved["models"]
                fetched_at = float(saved.get("fetchedAt") or 0.0)
                if cached_models:
                    source = "models.dev (cached)"
        except Exception:
            pass

    now = time.time()
    is_stale = (now - fetched_at) > CACHE_TTL_SEC or not cached_models
    if allow_network and (refresh or is_stale):
        try:
            raw_api = fetch_models_dev_json(timeout=timeout)
            extracted = extract_models_dev_rates(raw_api)
            if extracted:
                cached_models = extracted
                fetched_at = now
                source = "models.dev (live)"
                cf.parent.mkdir(parents=True, exist_ok=True)
                tmp = cf.with_suffix(".tmp")
                payload = {
                    "source": PRICES_URL,
                    "fetchedAt": fetched_at,
                    "models": cached_models,
                }
                tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                os.replace(tmp, cf)
        except Exception:
            pass

    merged = dict(FALLBACK_RATES)
    merged.update(cached_models)
    return {"source": source, "fetched_at": fetched_at, "models": merged}


def resolve_model_rate(model_name: str, price_table: Dict[str, Any]) -> Dict[str, Any]:
    """Resolves exact or family-level rate metadata for a model identifier."""
    models = price_table.get("models", FALLBACK_RATES)
    norm = normalize_model_key(model_name)

    if norm in models:
        return {**models[norm], "normalized": norm, "matched": "exact"}

    # Prefix match (handles dot/dash differences like gemini-4-hydrogen vs gemini-4-hydrogen-preview)
    for k in sorted(models.keys(), key=len, reverse=True):
        if norm.startswith(k) or k.startswith(norm):
            return {**models[k], "normalized": norm, "matched": "prefix"}

    # Family heuristics for uncatalogued Antigravity aliases
    if "opus" in norm:
        base = FALLBACK_RATES["claude-opus-4-6"]
        return {**base, "normalized": norm, "matched": "family"}
    if "claude" in norm or "sonnet" in norm:
        base = FALLBACK_RATES["claude-sonnet-4-6"]
        return {**base, "normalized": norm, "matched": "family"}
    if "haiku" in norm:
        base = FALLBACK_RATES["claude-haiku-4-5"]
        return {**base, "normalized": norm, "matched": "family"}
    if "flash" in norm or "carbon" in norm:
        base = FALLBACK_RATES["gemini-3.8-flash"]
        return {**base, "normalized": norm, "matched": "family"}
    if "gemini" in norm or "hydrogen" in norm or "neon" in norm:
        base = FALLBACK_RATES["gemini-4-hydrogen"]
        return {**base, "normalized": norm, "matched": "family"}

    return {"name": model_name or "Unknown", "input": 0.0, "cache_read": 0.0, "output": 0.0, "context_limit": 200_000, "normalized": norm, "matched": "unpriced"}


def calculate_turn_cost(
    model_name: str,
    input_tokens: int,
    cache_read_tokens: int,
    output_tokens: int,
    price_table: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Computes USD cost for a single turn where input_tokens represents uncached input
    and cache_read_tokens represents cached prompt tokens (matching transcript.jsonl).
    """
    rate = resolve_model_rate(model_name, price_table)
    inp_cost = (max(0, input_tokens) / 1_000_000.0) * rate["input"]
    cr_cost = (max(0, cache_read_tokens) / 1_000_000.0) * rate["cache_read"]
    out_cost = (max(0, output_tokens) / 1_000_000.0) * rate["output"]
    uncached_cr_cost = (max(0, cache_read_tokens) / 1_000_000.0) * rate["input"]
    total = inp_cost + cr_cost + out_cost
    savings = max(0.0, uncached_cr_cost - cr_cost)
    return {
        "input_cost": inp_cost,
        "cache_read_cost": cr_cost,
        "output_cost": out_cost,
        "total_cost": total,
        "cache_savings": savings,
        "context_limit": rate["context_limit"],
        "normalized_model": rate["normalized"],
        "rate_match": rate["matched"],
    }
