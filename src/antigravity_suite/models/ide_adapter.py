"""Adapter for managing Antigravity IDE configuration and cloud code proxy settings."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from antigravity_suite.config_paths import get_user_home

DEFAULT_CLOUD_CODE_URL = "http://127.0.0.1:50999"
CLOUD_CODE_KEY = "jetski.cloudCodeUrl"


def get_ide_settings_path() -> Path:
    """Returns the path to Antigravity IDE User settings.json."""
    custom_path = os.environ.get("ANTIGRAVITY_IDE_SETTINGS_PATH")
    if custom_path:
        return Path(custom_path).resolve()
    return get_user_home() / ".config" / "Antigravity IDE" / "User" / "settings.json"


def get_ide_backup_path(settings_path: Optional[Path] = None) -> Path:
    """Returns the path for backing up settings.json."""
    target = settings_path if settings_path else get_ide_settings_path()
    return target.parent / f"{target.name}.bak"


def _read_settings(path: Path) -> Dict[str, Any]:
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}


def _write_settings(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp.{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def apply_ide_proxy_url(
    proxy_url: str = DEFAULT_CLOUD_CODE_URL, settings_path: Optional[Path] = None
) -> Path:
    """Sets jetski.cloudCodeUrl in settings.json, creating a backup if none exists."""
    target = settings_path if settings_path else get_ide_settings_path()
    backup = get_ide_backup_path(target)
    if target.is_file() and not backup.exists():
        shutil.copy2(target, backup)
    settings = _read_settings(target)
    settings[CLOUD_CODE_KEY] = proxy_url
    _write_settings(target, settings)
    return target


def restore_ide_proxy_url(settings_path: Optional[Path] = None) -> bool:
    """Restores settings.json from backup or removes jetski.cloudCodeUrl."""
    target = settings_path if settings_path else get_ide_settings_path()
    backup = get_ide_backup_path(target)
    if backup.is_file():
        bak_data = _read_settings(backup)
        curr_data = _read_settings(target)
        if CLOUD_CODE_KEY in bak_data:
            curr_data[CLOUD_CODE_KEY] = bak_data[CLOUD_CODE_KEY]
        else:
            curr_data.pop(CLOUD_CODE_KEY, None)
        _write_settings(target, curr_data)
        backup.unlink(missing_ok=True)
        return True
    if target.is_file():
        curr_data = _read_settings(target)
        if CLOUD_CODE_KEY in curr_data:
            curr_data.pop(CLOUD_CODE_KEY, None)
            _write_settings(target, curr_data)
            return True
    return False


def get_ide_proxy_url(settings_path: Optional[Path] = None) -> Optional[str]:
    """Retrieves the current configured jetski.cloudCodeUrl if any."""
    target = settings_path if settings_path else get_ide_settings_path()
    settings = _read_settings(target)
    val = settings.get(CLOUD_CODE_KEY)
    return str(val) if val is not None else None
