"""CLI entry point and command router for Antigravity Custom Model Management."""

from __future__ import annotations

import argparse
import sys
from antigravity_suite.cli.models_ops import op_add_provider, op_fetch, op_list
from antigravity_suite.cli.models_proxy_ops import op_enable_all, op_ide, op_proxy, op_select, op_test


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Antigravity Custom Model Management CLI")
    p.add_argument(
        "action",
        nargs="?",
        default="list",
        choices=[
            "list", "status", "add-provider", "fetch", "enable-all", "select",
            "test", "proxy-status", "proxy-start", "proxy-stop", "apply-ide", "restore-ide"
        ],
        help="Model management action",
    )
    p.add_argument("--name", default="", help="Provider name")
    p.add_argument("--url", default="", help="Provider Base URL")
    p.add_argument("--token", default=None, help="Bearer API key or token")
    p.add_argument("--provider", default="", help="Target provider ID or name")
    p.add_argument("--model", default="gpt-4o", help="Model ID to test")
    p.add_argument("--models", default="", help="Comma-separated model IDs to select")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv or sys.argv[1:])

    if args.action in ["list", "status"]:
        return op_list()
    if args.action == "add-provider":
        if not args.name or not args.url:
            print("Error: --name and --url are required for add-provider.")
            return 1
        return op_add_provider(args.name, args.url, args.token)
    if args.action == "fetch":
        if not args.provider:
            print("Error: --provider is required for fetch.")
            return 1
        return op_fetch(args.provider)
    if args.action == "enable-all":
        if not args.provider:
            print("Error: --provider is required for enable-all.")
            return 1
        return op_enable_all(args.provider)
    if args.action == "select":
        if not args.provider or not args.models:
            print("Error: --provider and --models are required for select.")
            return 1
        return op_select(args.provider, [m.strip() for m in args.models.split(",") if m.strip()])
    if args.action == "test":
        target = args.provider or args.url
        if not target:
            print("Error: --provider or --url is required for test.")
            return 1
        return op_test(target, args.model)
    if args.action in ["proxy-status", "proxy-start", "proxy-stop"]:
        return op_proxy(args.action)
    if args.action in ["apply-ide", "restore-ide"]:
        return op_ide(args.action)
    return 0


if __name__ == "__main__":
    sys.exit(main())
