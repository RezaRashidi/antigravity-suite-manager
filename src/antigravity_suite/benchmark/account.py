"""
Account identity and quota benchmark collector.
"""

from __future__ import annotations

import json
import os
from typing import List

from .account_discovery import call_cloudcode_rpc, call_ls_rpc, find_ls_ports_and_csrf
from .models_system import AccountQuotaMetric, QuotaBucket


def _parse_quota_groups(groups: list) -> List[QuotaBucket]:
    buckets: List[QuotaBucket] = []
    for g in groups:
        gname = g.get("displayName", "")
        tag = "Gemini" if "Gemini" in gname else ("Claude/GPT" if ("Claude" in gname or "GPT" in gname) else "Global")
        for b in g.get("buckets", []):
            buckets.append(
                QuotaBucket(
                    group_name=tag,
                    name=b.get("displayName", "Limit"),
                    window=b.get("window", "unknown"),
                    remaining_fraction=float(b.get("remainingFraction", 0.0)),
                    reset_time=b.get("resetTime", ""),
                )
            )
    return buckets


def _collect_from_language_servers() -> List[AccountQuotaMetric]:
    metrics: List[AccountQuotaMetric] = []
    seen_emails = set()
    for pid, port, csrf in find_ls_ports_and_csrf():
        u = call_ls_rpc(port, csrf, "GetUserStatus")
        if not u or "userStatus" not in u:
            continue
        user = u.get("userStatus", {})
        email = user.get("email", "")
        if email in seen_emails:
            continue
        seen_emails.add(email)

        q = call_ls_rpc(port, csrf, "RetrieveUserQuotaSummary") or {}
        groups = q.get("response", {}).get("groups", [])
        plan = user.get("planStatus", {}).get("planInfo", {})
        metrics.append(
            AccountQuotaMetric(
                email=email,
                name=user.get("name", ""),
                tier=plan.get("teamsTier", "unknown"),
                plan_name=plan.get("planName", ""),
                buckets=_parse_quota_groups(groups),
                source=f"LanguageServer (PID {pid}, Port {port})",
            )
        )
    return metrics


def _collect_from_oauth_file() -> List[AccountQuotaMetric]:
    tok_path = os.path.expanduser("~/.gemini/jetski-standalone-oauth-token")
    if not os.path.isfile(tok_path):
        return []
    try:
        with open(tok_path, "r", encoding="utf-8") as f:
            d = json.load(f)
        acc_tok = d.get("token", {}).get("access_token", "")
        if not acc_tok:
            return []
        q = call_cloudcode_rpc(acc_tok, "retrieveUserQuotaSummary") or {}
        info = call_cloudcode_rpc(acc_tok, "fetchUserInfo") or {}
        assist = call_cloudcode_rpc(acc_tok, "loadCodeAssist") or {}
        tier = assist.get("currentTier", {}).get("name", "Antigravity")
        return [
            AccountQuotaMetric(
                email="OAuth Stored User",
                tier=tier,
                region_code=info.get("regionCode", ""),
                buckets=_parse_quota_groups(q.get("groups", [])),
                source="jetski-standalone-oauth-token",
            )
        ]
    except Exception:
        return []


def collect_accounts_and_quotas() -> List[AccountQuotaMetric]:
    res = _collect_from_language_servers()
    if not res:
        res = _collect_from_oauth_file()
    return res
