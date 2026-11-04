"""
Control Center action handler for Subagent Dynamic Multi-Account & Swarm Patch.
"""

from __future__ import annotations

import subprocess
from antigravity_suite.detect.constants import CYAN, NC


def handle_control_center_subagents_patch(manage_sh: str) -> None:
    print(f"\n{CYAN}--- Subagent Dynamic Multi-Account Allocator & Swarm Patch ---{NC}")
    print("  [1] Apply / Enable Subagent Dynamic Account Allocator (Idle Accounts + Swarm)")
    print("  [2] Revert / Disable Subagent Allocator (Standard Single-Account Mode)")
    print("  [3] View Subagent Allocator Policy & Quota Status")
    print("  [0] Return")
    c = input("Select action [1-3, Default: 1]: ").strip()
    if c in ["0"]:
        return
    if c == "2":
        subprocess.run(["bash", manage_sh, "unpatch-subagents"], check=False)
    elif c == "3":
        subprocess.run(["bash", manage_sh, "subagents", "--status"], check=False)
    else:
        subprocess.run(["bash", manage_sh, "subagents"], check=False)
    input("\nPress Enter to return to Control Center...")
