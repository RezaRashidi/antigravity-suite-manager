"""
Safety Backup Category Collector.

Populates safety tar archives with application profiles, configurations,
and conversation histories.
"""

from __future__ import annotations

import glob
import os
import tarfile
from antigravity_suite.migration.constants import (
    AGENTS_DIR,
    ANTIGRAVITY_CONF_DIR,
    CONFIG_DIR,
    GEMINI_DIR,
    MASTER_GEMINI,
    REAL_HOME,
)


def populate_safety_tar(tar: tarfile.TarFile, category: str) -> None:
    """Adds files and directories for the requested category to the tar archive."""
    from antigravity_suite.migration import safety
    real_home = getattr(safety, "REAL_HOME", None) or REAL_HOME

    if category in ["app", "all"]:
        app_cfg = os.path.join(real_home, ".config", "Antigravity")
        if os.path.isdir(app_cfg):
            tar.add(app_cfg, arcname="app/config_Antigravity", recursive=True)
        prof2 = os.path.join(real_home, ".antigravity-profile2")
        if os.path.isdir(prof2):
            tar.add(prof2, arcname="app/profile2", recursive=True)
        for d in glob.glob(os.path.join(real_home, ".antigravity-profile-app-*")):
            if os.path.isdir(d):
                tar.add(d, arcname=os.path.join("app/clones", os.path.basename(d)), recursive=True)

    if category in ["ide", "all"]:
        ide_cfg = os.path.join(real_home, ".config", "Antigravity IDE")
        if os.path.isdir(ide_cfg):
            tar.add(ide_cfg, arcname="ide/config_Antigravity_IDE", recursive=True)
        for item in ["gemide", "gemini-ide"]:
            p = os.path.join(real_home, f".{item}")
            if os.path.isdir(p):
                tar.add(p, arcname=f"ide/{item.replace('-', '_')}", recursive=True)
        ide_conv = os.path.join(GEMINI_DIR, "antigravity-ide")
        if os.path.isdir(ide_conv):
            tar.add(ide_conv, arcname="ide/antigravity_ide_conv", recursive=True)
        for d in glob.glob(os.path.join(real_home, ".antigravity-ide-profile-*")):
            if os.path.isdir(d):
                tar.add(d, arcname=os.path.join("ide/clones", os.path.basename(d)), recursive=True)

    if category in ["history", "all"] and MASTER_GEMINI and os.path.exists(MASTER_GEMINI):
        for item in ["conversations", "brain", "annotations"]:
            p = os.path.join(MASTER_GEMINI, item)
            if os.path.exists(p):
                tar.add(p, arcname=os.path.join("history", item), recursive=True)
        for sum_f in glob.glob(os.path.join(MASTER_GEMINI, "*summaries*")):
            if os.path.isfile(sum_f):
                tar.add(sum_f, arcname=os.path.join("history", os.path.basename(sum_f)))

    if category in ["suite", "configs", "all"]:
        if os.path.isfile(os.path.join(GEMINI_DIR, "GEMINI.md")):
            tar.add(os.path.join(GEMINI_DIR, "GEMINI.md"), arcname="suite/GEMINI.md")
        if os.path.isdir(CONFIG_DIR):
            tar.add(CONFIG_DIR, arcname="suite/config", recursive=True)
        if os.path.isdir(AGENTS_DIR):
            tar.add(AGENTS_DIR, arcname="suite/agents", recursive=True)
        if os.path.isdir(ANTIGRAVITY_CONF_DIR):
            for cf in glob.glob(os.path.join(ANTIGRAVITY_CONF_DIR, "*.conf")):
                tar.add(cf, arcname=os.path.join("suite", "config_antigravity", os.path.basename(cf)))
