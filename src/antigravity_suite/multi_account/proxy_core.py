"""Upstream request rewriter and token swapping engine for reverse proxy."""

from __future__ import annotations

import json
import re
from typing import Dict, Optional, Tuple
from antigravity_suite.multi_account.bindings import get_account_for_cascade
from antigravity_suite.multi_account.tokens import is_token_expired, refresh_access_token
from antigravity_suite.multi_account.vault import list_vault_accounts

DEFAULT_UPSTREAM = "https://daily-cloudcode-pa.googleapis.com"


def extract_cascade_id(body: bytes) -> Optional[str]:
    """Finds cascadeId or conversationId from JSON or string payload."""
    if not body:
        return None
    try:
        d = json.loads(body.decode("utf-8", "ignore"))
        cid = d.get("cascadeId") or d.get("conversationId") or d.get("trajectoryId")
        if cid and isinstance(cid, str):
            return cid
    except Exception:
        pass
    m = re.search(rb'"(?:cascadeId|conversationId)":\s*"([a-zA-Z0-9_\-]+)"', body)
    if m:
        return m.group(1).decode("utf-8", "ignore")
    return None


def resolve_account_token(cascade_id: Optional[str]) -> Optional[str]:
    """Resolves active OAuth access token for cascade_id or fallback primary."""
    email = get_account_for_cascade(cascade_id) if cascade_id else None
    accounts = list_vault_accounts()
    selected = None
    if email:
        for a in accounts:
            if a.email.lower() == email.lower():
                selected = a
                break
    if not selected:
        for a in accounts:
            if a.is_primary:
                selected = a
                break
    if not selected and accounts:
        selected = accounts[0]
    if not selected or not selected.token:
        return None

    tok = selected.token
    if is_token_expired(tok.expiry) and tok.refresh_token:
        ref = refresh_access_token(tok.refresh_token)
        if ref:
            tok.access_token, tok.expiry = ref[0], ref[1]
    return tok.access_token


def prepare_upstream_headers(
    headers: Dict[str, str], token: Optional[str], upstream_host: str
) -> Dict[str, str]:
    """Replaces Authorization header and strips loopback-specific headers."""
    out = dict(headers)
    out["Host"] = upstream_host
    if token:
        out["Authorization"] = f"Bearer {token}"
    for drop in ["Content-Length", "Transfer-Encoding", "Connection"]:
        out.pop(drop, None)
    return out
