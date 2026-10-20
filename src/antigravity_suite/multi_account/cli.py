"""Command-line interface for the Antigravity multi-account subsystem."""

from __future__ import annotations

import argparse
import json
import sys
from antigravity_suite.multi_account.bindings import (
    bind_cascade_to_account, get_account_for_cascade, load_bindings
)
from antigravity_suite.multi_account.models import AccountRecord
from antigravity_suite.multi_account.oauth import start_login_flow
from antigravity_suite.multi_account.proxy_server import run_proxy_server
from antigravity_suite.multi_account.quota import fetch_account_quotas, fetch_account_tier
from antigravity_suite.multi_account.service import is_proxy_running
from antigravity_suite.multi_account.vault import list_vault_accounts, remove_account_from_vault


def _cmd_list(args):
    accounts = list_vault_accounts()
    if not accounts:
        print("No accounts registered in vault.")
        return
    for a in accounts:
        fetch_account_quotas(a)
        fetch_account_tier(a)
        prim = " [PRIMARY]" if a.is_primary else ""
        print(f"* {a.email} ({a.name}) - {a.tier}{prim}")
        for q in a.quotas:
            print(f"    - {q.family:8} [{q.window:6}]: {q.percent()}% remaining")


def _cmd_json(args):
    accounts = list_vault_accounts()
    for a in accounts:
        fetch_account_quotas(a)
        fetch_account_tier(a)
    out = {
        "proxy_running": is_proxy_running(),
        "accounts": [a.to_dict() for a in accounts],
        "bindings": {k: b.email for k, b in load_bindings().items()},
    }
    print(json.dumps(out, indent=2))


def _cmd_login(args):
    print("Opening Google OAuth sign-in flow in default browser...")
    rec = start_login_flow(open_browser=True)
    if rec:
        print(f"Successfully added account: {rec.email}")
    else:
        print("Failed to authenticate account.")
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(description="Antigravity Multi-Account Tool")
    sub = p.add_subparsers(dest="subcommand")
    sub.add_parser("list")
    sub.add_parser("json")
    sub.add_parser("login")

    p_del = sub.add_parser("logout")
    p_del.add_argument("email", help="Account email to remove")

    p_bind = sub.add_parser("bind")
    p_bind.add_argument("cascade_id", help="Conversation ID")
    p_bind.add_argument("email", help="Account email")

    p_srv = sub.add_parser("serve")
    p_srv.add_argument("--port", type=int, default=41999)

    args = p.parse_args()
    if args.subcommand == "list":
        _cmd_list(args)
    elif args.subcommand == "json":
        _cmd_json(args)
    elif args.subcommand == "login":
        _cmd_login(args)
    elif args.subcommand == "logout":
        remove_account_from_vault(args.email)
        print(f"Removed account {args.email}")
    elif args.subcommand == "bind":
        bind_cascade_to_account(args.cascade_id, args.email)
        print(f"Bound {args.cascade_id} -> {args.email}")
    elif args.subcommand == "serve":
        srv = run_proxy_server(args.port)
        print(f"Antigravity multi-account proxy running on 127.0.0.1:{args.port}")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            srv.server_close()
    else:
        p.print_help()


if __name__ == "__main__":
    main()
