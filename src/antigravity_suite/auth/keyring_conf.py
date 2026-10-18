"""
Keyring configuration loading and persisting.
"""

from __future__ import annotations

import os
from typing import Dict
from antigravity_suite.auth.keyring_constants import CONF_DIR, KEYRING_CONF


def load_config() -> Dict[str, str]:
    """Loads current keyring mode configuration for all instances."""
    cfg = {"app1": "normal", "app2": "normal", "ide": "normal"}
    if os.path.isfile(KEYRING_CONF):
        try:
            with open(KEYRING_CONF, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'").lower()
                    if k == "KEYRING_MODE_APP1":
                        cfg["app1"] = v
                    elif k == "KEYRING_MODE_APP2":
                        cfg["app2"] = v
                    elif k == "KEYRING_MODE_IDE":
                        cfg["ide"] = v
        except Exception:
            pass
    return cfg


def save_config(cfg: Dict[str, str]) -> None:
    """Saves updated keyring mode configuration."""
    os.makedirs(CONF_DIR, exist_ok=True)
    with open(KEYRING_CONF, "w", encoding="utf-8") as f:
        f.write("# Antigravity Keyring Storage Configuration\n")
        f.write("# Values: 'normal' (Basic file storage, no GNOME Keyring) or 'gnome' (GNOME Keyring)\n")
        f.write(f'KEYRING_MODE_APP1="{cfg.get("app1", "normal")}"\n')
        f.write(f'KEYRING_MODE_APP2="{cfg.get("app2", "normal")}"\n')
        f.write(f'KEYRING_MODE_IDE="{cfg.get("ide", "normal")}"\n')
