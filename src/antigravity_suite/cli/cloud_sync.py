"""
CLI command dispatch for Antigravity Cloud Sync.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

from antigravity_suite.cloud.config_manager import load_remote_name, save_remote_name
from antigravity_suite.cloud.constants import BOLD, C, CONVERSATIONS_DIR, G, NC, R, Y
from antigravity_suite.cloud.rclone_client import is_rclone_installed, list_rclone_remotes
from antigravity_suite.cloud.sync_engine import execute_cloud_pull, execute_cloud_push


def _print_status(remote: str) -> None:
    installed = is_rclone_installed()
    remotes = list_rclone_remotes()
    c_count = len(glob.glob(os.path.join(CONVERSATIONS_DIR, "*.db"))) if os.path.isdir(CONVERSATIONS_DIR) else 0

    print(f"\n{C}====================================================={NC}")
    print(f"{BOLD}{C}      Antigravity Cloud Synchronization Status       {NC}")
    print(f"{C}====================================================={NC}")
    print(f"Rclone Binary:         {f'{G}Installed{NC}' if installed else f'{R}Missing{NC}'}")
    print(f"Configured Remote:     {BOLD}{remote}{NC} ({f'{G}Found in Rclone{NC}' if remote in remotes else f'{Y}Not Configured in Rclone{NC}'})")
    print(f"Available Remotes:     {', '.join(remotes) if remotes else 'None'}")
    print(f"Local Conversations:   {c_count} databases")
    print(f"{C}====================================================={NC}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Antigravity Cloud Synchronization")
    parser.add_argument("action", nargs="?", default="status", choices=["status", "push", "pull", "config", "set-remote"])
    parser.add_argument("param", nargs="?", default="")
    parser.add_argument("--remote", default="")
    args = parser.parse_args(argv or sys.argv[1:])

    remote = args.remote or args.param or load_remote_name()

    if args.action in ["config", "set-remote"]:
        if args.param:
            remote = save_remote_name(args.param)
            print(f"{G}[SUCCESS]{NC} Updated cloud remote to: {BOLD}{remote}{NC}")
        else:
            print(f"Current cloud remote: {BOLD}{remote}{NC}")
        return 0

    if args.action == "push":
        print(f"Pushing local conversation states to {BOLD}{remote}{NC}...")
        ok, msg, stats = execute_cloud_push(remote)
        if ok:
            print(f"{G}[SUCCESS]{NC} {msg} (Flushed WAL on {stats.get('wal_flushed', 0)} dbs)")
            return 0
        print(f"{R}[ERROR]{NC} {msg}")
        return 1

    if args.action == "pull":
        print(f"Pulling remote conversation states from {BOLD}{remote}{NC}...")
        ok, msg, stats = execute_cloud_pull(remote)
        if ok:
            print(f"{G}[SUCCESS]{NC} {msg}")
            print(f"  • Conversations Updated: {stats.get('applied', 0)}")
            print(f"  • Forked Divergences:   {stats.get('forked', 0)}")
            print(f"  • Workspaces Provisioned:{stats.get('workspaces_created', 0)}")
            return 0
        print(f"{R}[ERROR]{NC} {msg}")
        return 1

    _print_status(remote)
    return 0


if __name__ == "__main__":
    sys.exit(main())
