"""
App and IDE Data Deletion Engine.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess

from antigravity_suite.migration.constants import (
    GEMINI_DIR,
    REAL_HOME,
    log_info,
    log_success,
)
from antigravity_suite.migration.safety import create_safety_backup


def delete_app_data(backup: bool = True) -> bool:
    """Removes all Antigravity App configuration and profile directories."""
    log_info("Cleaning Antigravity Desktop App data and profiles...")
    if backup:
        create_safety_backup(category="app", label="pre_delete_app_data")

    try:
        subprocess.run(["pkill", "-f", "Antigravity.*user-data-dir"], check=False)
        subprocess.run(["pkill", "-f", "class=antigravity"], check=False)
    except Exception:
        pass

    from antigravity_suite.migration import cleanup
    real_home = getattr(cleanup, "REAL_HOME", None) or REAL_HOME

    targets = [
        os.path.join(real_home, ".config", "Antigravity"),
        os.path.join(real_home, ".antigravity-profile2"),
    ]
    targets.extend(glob.glob(os.path.join(real_home, ".antigravity-profile-app-*")))

    cleaned = 0
    for tgt in targets:
        if os.path.exists(tgt):
            if os.path.isdir(tgt) and not os.path.islink(tgt):
                shutil.rmtree(tgt, ignore_errors=True)
            else:
                try: os.remove(tgt)
                except Exception: pass
            cleaned += 1

    log_success(f"Antigravity App data cleaned ({cleaned} target paths removed).")
    return True


def delete_ide_data(backup: bool = True) -> bool:
    """Removes all Antigravity IDE configuration, workspace state, and profile directories."""
    log_info("Cleaning Antigravity IDE data and state...")
    if backup:
        create_safety_backup(category="ide", label="pre_delete_ide_data")

    try:
        subprocess.run(["pkill", "-f", "antigravity-ide"], check=False)
    except Exception:
        pass

    from antigravity_suite.migration import cleanup
    real_home = getattr(cleanup, "REAL_HOME", None) or REAL_HOME

    targets = [
        os.path.join(real_home, ".config", "Antigravity IDE"),
        os.path.join(real_home, ".gemide"),
        os.path.join(real_home, ".gemini-ide"),
        os.path.join(GEMINI_DIR, "antigravity-ide"),
    ]
    targets.extend(glob.glob(os.path.join(real_home, ".antigravity-ide-profile-*")))

    cleaned = 0
    for tgt in targets:
        if os.path.exists(tgt):
            if os.path.isdir(tgt) and not os.path.islink(tgt):
                shutil.rmtree(tgt, ignore_errors=True)
            else:
                try: os.remove(tgt)
                except Exception: pass
            cleaned += 1

    log_success(f"Antigravity IDE data cleaned ({cleaned} target paths removed).")
    return True
