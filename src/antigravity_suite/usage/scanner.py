"""
Read-only scanner for Antigravity transcript.jsonl files and multi-account bindings.
Aggregates daily/weekly/monthly/all-time tokens, Cache Hit Rate, and USD spend.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from antigravity_suite.detect.constants import REAL_HOME
from antigravity_suite.usage.pricing import calculate_turn_cost, load_price_table


def get_default_brain_dir() -> Path:
    return Path(REAL_HOME) / ".gemini" / "antigravity" / "brain"


def load_cascade_account_map(bindings_file: Optional[Path] = None) -> Dict[str, str]:
    """Maps cascade_id -> account email without requiring multi-account daemons."""
    candidates: List[Path] = []
    if bindings_file is not None:
        candidates.append(bindings_file)
    else:
        candidates.extend([
            Path(REAL_HOME) / ".config" / "antigravity" / "accounts" / "bindings.json",
            Path(REAL_HOME) / ".config" / "antigravity" / "multi_account_bindings.json",
        ])

    out: Dict[str, str] = {}
    for p in candidates:
        if not p.is_file():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        for k, v in raw.items():
            if k.startswith("__"):
                continue
            if isinstance(v, dict) and v.get("email"):
                out[k] = str(v["email"])
            elif isinstance(v, str) and v:
                out[k] = v
        if out:
            break
    return out


def _parse_iso_to_local(ts_str: Any) -> Optional[datetime]:
    if not isinstance(ts_str, str) or not ts_str.strip():
        return None
    s = ts_str.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone()
    except Exception:
        return None


def _extract_tokens(row: Dict[str, Any]) -> Optional[Tuple[int, int, int]]:
    """Extracts (input_tokens, cache_read_tokens, output_tokens) across Desktop & CLI formats."""
    if any(k in row for k in ("input_tokens", "cache_read_tokens", "output_tokens")):
        inp = int(row.get("input_tokens") or 0)
        cr = int(row.get("cache_read_tokens") or 0)
        out = int(row.get("output_tokens") or 0)
        if inp == 0 and cr == 0 and out == 0:
            return None
        return max(0, inp), max(0, cr), max(0, out)

    for usage_container in (
        row.get("usage"),
        (row.get("chatModel") or {}).get("usage") if isinstance(row.get("chatModel"), dict) else None,
        (row.get("plannerResponse") or {}).get("usage") if isinstance(row.get("plannerResponse"), dict) else None,
    ):
        if isinstance(usage_container, dict):
            inp = int(usage_container.get("inputTokens") or usage_container.get("promptTokenCount") or 0)
            cr = int(usage_container.get("cacheReadTokens") or usage_container.get("cachedContentTokenCount") or 0)
            out = int(usage_container.get("outputTokens") or usage_container.get("candidatesTokenCount") or 0)
            if inp or cr or out:
                return max(0, inp), max(0, cr), max(0, out)
    return None


def _empty_bucket() -> Dict[str, Any]:
    return {
        "turns": 0,
        "input_tokens": 0,
        "cache_read_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "cache_savings_usd": 0.0,
    }


def _add_to_bucket(bucket: Dict[str, Any], inp: int, cr: int, out: int, cost: float, savings: float) -> None:
    bucket["turns"] += 1
    bucket["input_tokens"] += inp
    bucket["cache_read_tokens"] += cr
    bucket["output_tokens"] += out
    bucket["total_tokens"] += inp + cr + out
    bucket["cost_usd"] += cost
    bucket["cache_savings_usd"] += savings


def _finalize_bucket(b: Dict[str, Any]) -> Dict[str, Any]:
    prompt_total = b["input_tokens"] + b["cache_read_tokens"]
    hit_rate = (b["cache_read_tokens"] / prompt_total * 100.0) if prompt_total > 0 else 0.0
    return {
        **b,
        "prompt_tokens": prompt_total,
        "cache_hit_rate": round(hit_rate, 2),
        "cost_usd": round(b["cost_usd"], 6),
        "cache_savings_usd": round(b["cache_savings_usd"], 6),
    }


def scan_usage(
    days: Optional[int] = None,
    account_filter: Optional[str] = None,
    model_filter: Optional[str] = None,
    brain_dir: Optional[Path] = None,
    bindings_file: Optional[Path] = None,
    refresh_prices: bool = False,
    allow_network: bool = True,
    price_cache_file: Optional[Path] = None,
    now_local: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Scans all transcript.jsonl logs and aggregates usage, Cache Hit Rate, and USD costs."""
    bdir = brain_dir or get_default_brain_dir()
    now = now_local or datetime.now().astimezone()
    today_date = now.date()
    cutoff_filter = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0) if days is not None else None

    price_table = load_price_table(refresh=refresh_prices, allow_network=allow_network, cache_file=price_cache_file)
    bindings = load_cascade_account_map(bindings_file=bindings_file)

    windows = {
        "today": _empty_bucket(),
        "7d": _empty_bucket(),
        "30d": _empty_bucket(),
        "all": _empty_bucket(),
    }
    filtered_totals = _empty_bucket()
    by_account: Dict[str, Dict[str, Any]] = defaultdict(_empty_bucket)
    by_model: Dict[str, Dict[str, Any]] = defaultdict(_empty_bucket)
    by_day: Dict[str, Dict[str, Any]] = defaultdict(_empty_bucket)
    matched_cascades: Set[str] = set()
    active_days_all: Set[str] = set()
    files_scanned = 0

    transcript_paths: List[Path] = []
    if bdir.is_dir():
        for entry in bdir.iterdir():
            if not entry.is_dir():
                continue
            cand = entry / ".system_generated" / "logs" / "transcript.jsonl"
            if cand.is_file():
                transcript_paths.append(cand)

    acct_q = account_filter.strip().lower() if account_filter else None
    model_q = model_filter.strip().lower() if model_filter else None

    for tpath in transcript_paths:
        files_scanned += 1
        cascade_id = tpath.parent.parent.parent.name
        account = bindings.get(cascade_id, "unbound")
        if acct_q and acct_q not in account.lower():
            continue

        seen_steps: Set[Any] = set()
        last_model = "unknown"
        fallback_dt = datetime.fromtimestamp(tpath.stat().st_mtime).astimezone()

        try:
            with tpath.open("r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(row, dict):
                        continue

                    raw_model = row.get("model") or (row.get("chatModel") or {}).get("model")
                    if isinstance(raw_model, str) and raw_model.strip():
                        last_model = raw_model.strip()

                    tokens = _extract_tokens(row)
                    if tokens is None:
                        continue

                    step_key = row.get("step_index")
                    if step_key is not None:
                        dedup_key = (cascade_id, step_key)
                        if dedup_key in seen_steps:
                            continue
                        seen_steps.add(dedup_key)
                    else:
                        dedup_key = (cascade_id, f"line:{idx}")

                    model_name = last_model
                    if model_q and model_q not in model_name.lower():
                        continue

                    dt = _parse_iso_to_local(row.get("created_at") or row.get("timestamp")) or fallback_dt
                    day_str = dt.date().isoformat()
                    active_days_all.add(day_str)

                    inp, cr, out = tokens
                    cost_info = calculate_turn_cost(model_name, inp, cr, out, price_table)
                    cost_usd = cost_info["total_cost"]
                    savings_usd = cost_info["cache_savings"]

                    _add_to_bucket(windows["all"], inp, cr, out, cost_usd, savings_usd)
                    if dt.date() == today_date:
                        _add_to_bucket(windows["today"], inp, cr, out, cost_usd, savings_usd)
                    if dt >= (now - timedelta(days=7)):
                        _add_to_bucket(windows["7d"], inp, cr, out, cost_usd, savings_usd)
                    if dt >= (now - timedelta(days=30)):
                        _add_to_bucket(windows["30d"], inp, cr, out, cost_usd, savings_usd)

                    if cutoff_filter is not None and dt < cutoff_filter:
                        continue

                    matched_cascades.add(cascade_id)
                    _add_to_bucket(filtered_totals, inp, cr, out, cost_usd, savings_usd)
                    _add_to_bucket(by_account[account], inp, cr, out, cost_usd, savings_usd)
                    _add_to_bucket(by_model[model_name], inp, cr, out, cost_usd, savings_usd)
                    _add_to_bucket(by_day[day_str], inp, cr, out, cost_usd, savings_usd)
        except OSError:
            continue

    acct_rows = [
        {"account": k, **_finalize_bucket(v)}
        for k, v in sorted(by_account.items(), key=lambda kv: (-kv[1]["cost_usd"], -kv[1]["total_tokens"]))
    ]
    model_rows = [
        {"model": k, **_finalize_bucket(v)}
        for k, v in sorted(by_model.items(), key=lambda kv: (-kv[1]["cost_usd"], -kv[1]["total_tokens"]))
    ]
    day_rows = [
        {"date": k, **_finalize_bucket(v)}
        for k, v in sorted(by_day.items())
    ]

    return {
        "generated_at": now.isoformat(),
        "brain_dir": str(bdir),
        "filter_days": days,
        "account_filter": account_filter,
        "model_filter": model_filter,
        "files_scanned": files_scanned,
        "cascades_with_usage": len(matched_cascades),
        "active_days": len(active_days_all),
        "pricing_source": price_table.get("source", "fallback"),
        "windows": {k: _finalize_bucket(v) for k, v in windows.items()},
        "totals": _finalize_bucket(filtered_totals),
        "by_account": acct_rows,
        "by_model": model_rows,
        "by_day": day_rows,
    }
