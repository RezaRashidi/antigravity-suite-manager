"""
Configuration loading and saving for Antigravity engine and installation paths.
"""

from __future__ import annotations

import os
from typing import List, Tuple

from antigravity_suite.detect.constants import CONF_DIR, PATHS_CONF
from antigravity_suite.detect.scan import scan_installations


def load_paths_config(detected_app: str = "", detected_ide: str = "") -> Tuple[str, str, List[str]]:
    app_dir = ""
    ide_dir = ""
    custom_paths: List[str] = []
    if os.path.isfile(PATHS_CONF):
        try:
            with open(PATHS_CONF, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k == "APP_INSTALL_DIR" and v:
                        app_dir = v
                    elif k == "IDE_INSTALL_DIR" and v:
                        ide_dir = v
                    elif k in ["CUSTOM_PATHS", "CUSTOM_ANTIGRAVITY_PATHS"] and v:
                        custom_paths = [p.strip() for p in v.split(":") if p.strip()]
        except Exception:
            pass

    if (not app_dir or not os.path.isdir(app_dir)) or (not ide_dir or not os.path.isdir(ide_dir)):
        if not detected_app or not detected_ide:
            for inst in scan_installations():
                if ("App" in inst["type"] or "Manager" in inst["type"]) and not detected_app:
                    detected_app = inst["path"]
                elif "IDE" in inst["type"] and not detected_ide:
                    detected_ide = inst["path"]

    env_app = os.environ.get("ANTIGRAVITY_APP_DIR", "")
    env_ide = os.environ.get("ANTIGRAVITY_IDE_DIR", "")
    if env_app and os.path.isdir(env_app):
        app_dir = env_app
    if env_ide and os.path.isdir(env_ide):
        ide_dir = env_ide

    final_app = app_dir if (app_dir and os.path.isdir(app_dir)) else (detected_app if (detected_app and os.path.isdir(detected_app)) else app_dir)
    if not final_app:
        for cand in ["/opt/Antigravity-x64", "/opt/antigravity2", "/opt/antigravity"]:
            if os.path.isdir(cand):
                final_app = cand
                break
        else:
            final_app = detected_app or "/opt/Antigravity-x64"

    final_ide = ide_dir if (ide_dir and os.path.isdir(ide_dir)) else (detected_ide if (detected_ide and os.path.isdir(detected_ide)) else ide_dir)
    if not final_ide:
        for cand in ["/opt/antigravity-ide", "/opt/antigravity", "/opt/antigravity2"]:
            if os.path.isdir(cand):
                final_ide = cand
                break
        else:
            final_ide = detected_ide or "/opt/antigravity-ide"

    return final_app, final_ide, custom_paths


def save_paths_config(app_dir: str, ide_dir: str, custom_paths: List[str] | None = None) -> None:
    os.makedirs(CONF_DIR, exist_ok=True)
    if custom_paths is None:
        custom_paths = []
    filtered = [p for p in custom_paths if p and p != app_dir and p != ide_dir]
    custom_str = ":".join(filtered)
    with open(PATHS_CONF, "w", encoding="utf-8") as f:
        f.write("# Antigravity Suite Installation Paths Configuration\n")
        f.write(f'APP_INSTALL_DIR="{app_dir}"\n')
        f.write(f'IDE_INSTALL_DIR="{ide_dir}"\n')
        f.write(f'CUSTOM_ANTIGRAVITY_PATHS="{custom_str}"\n')
