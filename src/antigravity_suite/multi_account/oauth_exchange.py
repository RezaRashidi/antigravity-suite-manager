"""OAuth Token Exchange Engine."""

from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Optional

from antigravity_suite.multi_account.models import AccountRecord, AccountToken
from antigravity_suite.multi_account.tokens import get_oauth_credentials, parse_jwt_claims
from antigravity_suite.multi_account.vault import save_account_to_vault


def exchange_auth_code(code: str, redirect_uri: str) -> Optional[AccountRecord]:
    cid, sec = get_oauth_credentials()
    if not cid or not sec:
        print("[OAuth] Error: Missing Google OAuth Client ID or Secret", file=sys.stderr)
        return None

    if not os.environ.get("https_proxy") and os.environ.get("ide_http_proxy"):
        os.environ["https_proxy"] = os.environ["ide_http_proxy"]
    if not os.environ.get("http_proxy") and os.environ.get("ide_http_proxy"):
        os.environ["http_proxy"] = os.environ["ide_http_proxy"]

    payload = {"code": code, "client_id": cid, "client_secret": sec, "redirect_uri": redirect_uri, "grant_type": "authorization_code"}
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=urllib.parse.urlencode(payload).encode("utf-8"), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            exp_in = d.get("expires_in", 3600)
            exp_dt = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=exp_in)).strftime("%Y-%m-%dT%H:%M:%S.000000+00:00")
            claims = parse_jwt_claims(d.get("id_token", ""))
            email = claims.get("email", "")
            if not email:
                print("[OAuth] Error: No email claim in id_token", file=sys.stderr)
                return None
            rec = AccountRecord(
                email=email, name=claims.get("name", email.split("@")[0]), sub=claims.get("sub", ""),
                token=AccountToken(d.get("access_token", ""), d.get("refresh_token", ""), exp_dt), id_token=d.get("id_token", ""),
            )
            save_account_to_vault(rec)
            print(f"[OAuth] Successfully saved account {email} to vault", file=sys.stderr)

            try:
                notify_req = urllib.request.Request("http://127.0.0.1:41999/api/multi-account/state?refresh=1", method="GET")
                with urllib.request.urlopen(notify_req, timeout=2) as _: pass
            except Exception: pass

            return rec
    except Exception as e:
        print(f"[OAuth] Token exchange failed: {e}", file=sys.stderr)
        return None
