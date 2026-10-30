"""
Action handlers for applying, reverting, and updating patches on unified instances.
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict

from antigravity_suite.detect.constants import CYAN, NC
from antigravity_suite.detect.unified_patches_helpers import (
    handle_unified_patch_fork,
    handle_unified_patch_models,
    handle_unified_patch_open_ide,
    handle_unified_patch_selector,
)


def handle_unified_patches_and_reinstall(choice: str, u_item: Dict[str, Any], eng_p: str, manage_sh: str) -> None:
    c_type = "ide" if "IDE" in u_item.get("type", "") else "app"
    flag = "--ide-dir" if c_type == "ide" else "--app-dir"
    up = choice.upper()

    if choice in ["8", "5"]:
        print(f"\n{CYAN}Downloading & installing fresh {u_item['type']} into {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "install", c_type, flag, eng_p, "--force"], check=False)
    elif up == "U":
        print(f"\n{CYAN}Smart updating {u_item['type']} at {eng_p} with force re-patch...{NC}")
        subprocess.run(["bash", manage_sh, "update", c_type, flag, eng_p, "--force"], check=False)
    elif up == "R":
        print(f"\n{CYAN}Applying RTL patch to {u_item['type']} at {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "rtl", c_type, flag, eng_p, "--force"], check=False)
    elif up in ["UNPATCH-RTL", "UR"]:
        print(f"\n{CYAN}Reverting RTL patch from {u_item['type']} at {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "unpatch-rtl", c_type, flag, eng_p], check=False)
    elif up == "F" and "IDE" not in u_item.get("type", ""):
        print(f"\n{CYAN}Applying F5 reload & isolation patch to {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "f5", "--app-dir", eng_p, "--force"], check=False)
    elif up in ["UNPATCH-F5", "UF"] and "IDE" not in u_item.get("type", ""):
        print(f"\n{CYAN}Reverting F5 reload patch from {eng_p}...{NC}")
        subprocess.run(["bash", manage_sh, "unpatch-f5", "--app-dir", eng_p], check=False)
    elif up == "J":
        handle_unified_patch_fork(c_type, flag, u_item, eng_p, manage_sh)
    elif up == "T":
        handle_unified_patch_selector(c_type, flag, u_item, eng_p, manage_sh)
    elif up in ["CM", "MODELS"]:
        handle_unified_patch_models(u_item, eng_p, manage_sh)
    elif up == "Y":
        handle_unified_patch_open_ide(u_item, eng_p, manage_sh)
