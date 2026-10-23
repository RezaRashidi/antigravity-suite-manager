"""
App and IDE Restoration Engine from Backups.
"""

from __future__ import annotations

import glob
import os
import shutil

from antigravity_suite.migration.constants import (
    REAL_HOME,
    get_gemini_dir,
    log_info,
    log_success,
)


def restore_app_files(app_dir: str) -> None:
    """Restores Antigravity App configurations, profiles, and clones from snapshot."""
    log_info("Restoring Antigravity App configurations and profiles...")
    cfg_src = os.path.join(app_dir, "config_Antigravity")
    if os.path.isdir(cfg_src):
        shutil.copytree(cfg_src, os.path.join(REAL_HOME, ".config", "Antigravity"), dirs_exist_ok=True)
    prof2_src = os.path.join(app_dir, "profile2")
    if os.path.isdir(prof2_src):
        shutil.copytree(prof2_src, os.path.join(REAL_HOME, ".antigravity-profile2"), dirs_exist_ok=True)
    clones_src = os.path.join(app_dir, "clones")
    if os.path.isdir(clones_src):
        for item in glob.glob(os.path.join(clones_src, "*")):
            dst = os.path.join(REAL_HOME, os.path.basename(item))
            if os.path.isdir(item):
                shutil.copytree(item, dst, dirs_exist_ok=True)
    log_success("Antigravity App configurations restored.")


def restore_ide_files(ide_dir: str) -> None:
    """Restores Antigravity IDE configurations and state from snapshot."""
    log_info("Restoring Antigravity IDE configurations and state...")
    cfg_src = os.path.join(ide_dir, "config_Antigravity_IDE")
    if os.path.isdir(cfg_src):
        shutil.copytree(cfg_src, os.path.join(REAL_HOME, ".config", "Antigravity IDE"), dirs_exist_ok=True)
    for name in ["gemide", "gemini_ide"]:
        src = os.path.join(ide_dir, name)
        if os.path.isdir(src):
            dst = os.path.join(REAL_HOME, f".{name.replace('_', '-')}")
            shutil.copytree(src, dst, dirs_exist_ok=True)
    ide_conv_src = os.path.join(ide_dir, "antigravity_ide_conv")
    if os.path.isdir(ide_conv_src):
        shutil.copytree(ide_conv_src, os.path.join(get_gemini_dir(), "antigravity-ide"), dirs_exist_ok=True)
    clones_src = os.path.join(ide_dir, "clones")
    if os.path.isdir(clones_src):
        for item in glob.glob(os.path.join(clones_src, "*")):
            dst = os.path.join(REAL_HOME, os.path.basename(item))
            if os.path.isdir(item):
                shutil.copytree(item, dst, dirs_exist_ok=True)
    log_success("Antigravity IDE configurations restored.")
