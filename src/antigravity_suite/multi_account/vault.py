"""Account storage and vault repository for Antigravity multi-account."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from antigravity_suite.multi_account.models import AccountRecord, AccountToken
from antigravity_suite.multi_account.tokens import parse_jwt_claims


def get_accounts_dir() -> Path:
    env_dir = os.environ.get("ANTIGRAVITY_ACCOUNTS_DIR")
    if env_dir:
        p = Path(env_dir)
    else:
        real_h = Path(os.environ["REAL_HOME"]) if "REAL_HOME" in os.environ else Path.home()
        p = real_h / ".config" / "antigravity" / "accounts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_account_from_file(path: Path) -> Optional[AccountRecord]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        tok_d = d.get("token", {})
        acc_tok = AccountToken(
            access_token=tok_d.get("access_token", ""),
            refresh_token=tok_d.get("refresh_token", ""),
            expiry=tok_d.get("expiry", ""),
            token_type=tok_d.get("token_type", "Bearer"),
        )
        claims = parse_jwt_claims(d.get("id_token", ""))
        email = d.get("email") or claims.get("email", "")
        if not email:
            return None
        return AccountRecord(
            email=email,
            name=d.get("name") or claims.get("name", email.split("@")[0]),
            sub=d.get("sub") or claims.get("sub", ""),
            token=acc_tok,
            id_token=d.get("id_token", ""),
            auth_method=d.get("auth_method", "consumer"),
            plan=d.get("plan", "Unknown"),
            tier=d.get("tier", "UNKNOWN_TIER"),
        )
    except Exception:
        return None


def save_account_to_vault(rec: AccountRecord) -> Path:
    target = get_accounts_dir() / f"{rec.email}.json"
    data = {
        "email": rec.email,
        "name": rec.name,
        "sub": rec.sub,
        "token": rec.token.to_dict() if rec.token else {},
        "id_token": rec.id_token,
        "auth_method": rec.auth_method,
        "plan": rec.plan,
        "tier": rec.tier,
    }
    tmp = target.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(target)
    return target


def list_vault_accounts() -> List[AccountRecord]:
    accounts: Dict[str, AccountRecord] = {}
    for p in get_accounts_dir().glob("*.json"):
        if p.name != "bindings.json" and p.name != "oauth_credentials.json":
            acc = load_account_from_file(p)
            if acc:
                accounts[acc.email] = acc
    homes = [Path.home()]
    if "REAL_HOME" in os.environ and Path(os.environ["REAL_HOME"]).is_dir():
        homes.append(Path(os.environ["REAL_HOME"]))
    for h in homes:
        for prim_p in h.glob(".*/jetski-standalone-oauth-token"):
            prim_acc = load_account_from_file(prim_p)
            if prim_acc:
                prim_acc.is_primary = True
                accounts.setdefault(prim_acc.email, prim_acc)
                accounts[prim_acc.email].is_primary = True
    return list(accounts.values())


def remove_account_from_vault(email: str) -> bool:
    target = get_accounts_dir() / f"{email}.json"
    if target.is_file():
        target.unlink()
        return True
    return False
