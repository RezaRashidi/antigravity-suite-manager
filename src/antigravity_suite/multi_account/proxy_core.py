"""Upstream request rewriter and token swapping engine for reverse proxy."""

from __future__ import annotations

import json
import re
from typing import Dict, Optional
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
    """Resolves OAuth token for cascade; returns None for transparent passthrough."""
    if not cascade_id:
        return None
    email = get_account_for_cascade(cascade_id)
    if not email:
        return None
    accounts = list_vault_accounts()
    selected = next((a for a in accounts if a.email.lower() == email.lower()), None)
    if not selected or selected.is_primary or not selected.token:
        return None

    tok = selected.token
    if is_token_expired(tok.expiry) and tok.refresh_token:
        ref = refresh_access_token(tok.refresh_token)
        if ref:
            tok.access_token, tok.expiry = ref[0], ref[1]
    return tok.access_token


def prepare_upstream_headers(
    headers: Dict[str, str], token: Optional[str], upstream_host: str, body_len: int = 0
) -> Dict[str, str]:
    """Prepares headers for upstream request; preserves Content-Length when body present."""
    out = dict(headers)
    out["Host"] = upstream_host
    if token:
        out["Authorization"] = f"Bearer {token}"
    if body_len > 0:
        out["Content-Length"] = str(body_len)
    else:
        out.pop("Content-Length", None)
    for drop in ["Transfer-Encoding", "Connection"]:
        out.pop(drop, None)
    return out
