"""
CLI handler for Antigravity keyring configuration and secret management.
"""

from __future__ import annotations

import argparse
import sys
from antigravity_suite.auth.keyring_apply import apply_mode_for_app1, apply_mode_for_app2, apply_mode_for_ide
from antigravity_suite.auth.keyring_clones import apply_mode_for_clones
from antigravity_suite.auth.keyring_conf import load_config, save_config
from antigravity_suite.auth.keyring_constants import GREEN, NC, YELLOW
from antigravity_suite.auth.keyring_purge import purge_antigravity_from_keyring
from antigravity_suite.auth.keyring_status import inspect_status


def build_parser() -> argparse.ArgumentParser:
    """Constructs the CLI argument parser for keyring management."""
    parser = argparse.ArgumentParser(description="Antigravity Keyring Mode Switcher")
    subparsers = parser.add_subparsers(dest="action")
    subparsers.add_parser("status", help="Show keyring mode and inspect GNOME Keyring items")
    set_p = subparsers.add_parser("set", help="Set keyring mode for instance(s)")
    set_p.add_argument("target", choices=["app1", "app2", "ide", "all"], help="Target instance")
    set_p.add_argument("mode", choices=["normal", "basic", "plain", "gnome", "keyring"], help="Storage mode")
    set_p.add_argument("--purge", action="store_true", help="Purge item from GNOME Keyring after switching to normal")
    subparsers.add_parser("purge", help="Delete all Antigravity items from GNOME Keyring")
    return parser


def handle_set(target: str, mode: str, purge: bool) -> None:
    """Executes mode switching for specified targets."""
    cfg = load_config()
    norm = "normal" if mode in ["normal", "basic", "plain"] else "gnome"
    if target in ["app1", "all"]:
        cfg["app1"] = norm
        apply_mode_for_app1(norm)
        print(f"{GREEN}[OK]{NC} Switched Account 1 to {norm.upper()} mode.")
    if target in ["app2", "all"]:
        cfg["app2"] = norm
        apply_mode_for_app2(norm)
        print(f"{GREEN}[OK]{NC} Switched Account 2 to {norm.upper()} mode.")
    if target in ["ide", "all"]:
        cfg["ide"] = norm
        apply_mode_for_ide(norm)
        print(f"{GREEN}[OK]{NC} Switched Antigravity IDE to {norm.upper()} mode.")
    if target == "all":
        apply_mode_for_clones(norm)
    save_config(cfg)
    if norm == "normal" and purge:
        print(f"\n{YELLOW}Purging Antigravity items for {target} from GNOME Keyring...{NC}")
        purge_antigravity_from_keyring(target)
    print("\nUpdated Status:")
    inspect_status()


def main(args: list[str] | None = None) -> int:
    """Main CLI execution entry point."""
    parsed = build_parser().parse_args(args)
    if parsed.action in ["status", None]:
        inspect_status()
    elif parsed.action == "purge":
        inspect_status()
        print(f"\n{YELLOW}Purging Antigravity secrets from GNOME Keyring...{NC}")
        cnt = purge_antigravity_from_keyring()
        print(f"{GREEN}[SUCCESS] Purged {cnt} items from GNOME Keyring.{NC}\n\nUpdated Status:")
        inspect_status()
    elif parsed.action == "set":
        handle_set(parsed.target, parsed.mode, parsed.purge)
    return 0
