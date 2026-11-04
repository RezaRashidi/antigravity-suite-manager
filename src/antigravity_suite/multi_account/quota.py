"""Quota telemetry fetching and parsing for multi-account accounts."""

from __future__ import annotations

import json
import urllib.request
from typing import List, Optional
from antigravity_suite.multi_account.models import AccountRecord, QuotaBucket
from antigravity_suite.multi_account.tokens import is_token_expired, refresh_access_token


def parse_quota_buckets(groups: list) -> List[QuotaBucket]:
    buckets: List[QuotaBucket] = []
    for g in groups:
        gname = g.get("displayName", "")
        family = "gemini" if "Gemini" in gname else ("claude" if ("Claude" in gname or "GPT" in gname) else "other")
        for b in g.get("buckets", []):
            win = b.get("window", "").lower()
            tag_win = "5h" if ("5h" in win or "5 hour" in win or "five" in win) else "weekly"
            buckets.append(
                QuotaBucket(
                    family=family,
                    window=tag_win,
                    fraction=float(b.get("remainingFraction", 1.0)),
                    reset_time=b.get("resetTime", ""),
                )
            )
    return buckets


def fetch_account_quotas(account: AccountRecord) -> List[QuotaBucket]:
    if not account.token or not account.token.access_token:
        return []
    if is_token_expired(account.token.expiry) and account.token.refresh_token:
        res = refresh_access_token(account.token.refresh_token)
        if res:
            account.token.access_token, account.token.expiry = res[0], res[1]

    url = "https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary"
    req = urllib.request.Request(
        url,
        data=b"{}",
        headers={
            "Authorization": f"Bearer {account.token.access_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8", "ignore"))
            groups = data.get("groups", [])
            buckets = parse_quota_buckets(groups)
            account.quotas = buckets
            return buckets
    except Exception:
        return []


def fetch_account_tier(account: AccountRecord) -> str:
    if not account.token or not account.token.access_token:
        return account.tier
    url = "https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"
    req = urllib.request.Request(
        url,
        data=b"{}",
        headers={
            "Authorization": f"Bearer {account.token.access_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8", "ignore"))
            # Native Google AI Pro detection from paidTier / g1Tier
            paid = data.get("paidTier") or data.get("g1Tier") or data.get("userTier")
            if paid and (paid.get("name") or paid.get("id")):
                name = paid.get("name") or paid.get("id") or ""
                account.plan = paid.get("name", "Google AI Pro")
                account.tier = "PRO" if ("pro" in name.lower() or "g1" in name.lower()) else name
                return account.tier
            allowed = data.get("allowedTiers", [])
            for t in allowed:
                tid = t.get("id", "")
                tname = t.get("name", "")
                if tid in ["standard-tier", "g1-pro-tier"] or "code assist" in tname.lower():
                    account.plan = "Google AI Pro"
                    account.tier = "PRO"
                    return "PRO"
    except Exception:
        pass
    if any(q.family == "claude" for q in account.quotas) or len(account.quotas) >= 4:
        account.plan = "Google AI Pro"
        account.tier = "PRO"
        return "PRO"
    return account.tier
