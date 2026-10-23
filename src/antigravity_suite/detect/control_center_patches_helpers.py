"""
Target dispatch helper for patch execution across detected instances.
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict, List, Optional
from antigravity_suite.detect.constants import BOLD, NC, RED


def run_target_patch(manage_sh: str, action_cmd: str, unified: Optional[List[Dict[str, Any]]], name: str, force: bool = True) -> None:
    """Prompts user to select instance targets and invokes manage.sh patch action."""
    force_flags = ["--force"] if force else []
    if unified and len(unified) > 0:
        print(f"\n{BOLD}Target Instances for {name}:{NC}")
        print("  [A] All Detected Instances (IDE & App)")
        for idx, item in enumerate(unified, 1):
            print(f"  [{idx}] {item['name']} ({item['type']}) at {item['engine_path']}")
        print("  [0] Cancel")
        t_choice = input(f"Select target [A, 1-{len(unified)}, Default: A]: ").strip()
        if t_choice in ["0"]:
            return
        if t_choice.upper() in ["A", ""]:
            subprocess.run(["bash", manage_sh, action_cmd, "all"] + force_flags, check=False)
        elif t_choice.isdigit() and 1 <= int(t_choice) <= len(unified):
            target = unified[int(t_choice) - 1]
            itype = "ide" if "IDE" in target.get("type", "") else "app"
            dir_flag = "--ide-dir" if itype == "ide" else "--app-dir"
            subprocess.run(["bash", manage_sh, action_cmd, itype, dir_flag, target["engine_path"]] + force_flags, check=False)
        else:
            print(f"{RED}[ERROR] Invalid target selection.{NC}")
    else:
        subprocess.run(["bash", manage_sh, action_cmd, "all"] + force_flags, check=False)
    input("\nPress Enter to return to Control Center...")
