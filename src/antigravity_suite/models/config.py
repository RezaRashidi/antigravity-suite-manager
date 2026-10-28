"""Configuration manager for Antigravity custom models."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from antigravity_suite.config_paths import get_user_home

DEFAULT_CONFIG_FILENAME = "custom_models.json"


def get_custom_models_path() -> Path:
    """Discovers the path to custom_models.json."""
    custom_env = os.environ.get("ANTIGRAVITY_CUSTOM_MODELS_PATH")
    if custom_env:
        return Path(custom_env).resolve()
    data_dir = os.environ.get("ANTIGRAVITY_DATA_DIR")
    if data_dir:
        return Path(data_dir).resolve() / DEFAULT_CONFIG_FILENAME
    gemini_dir = os.environ.get("ANTIGRAVITY_GEMINI_DIR")
    if gemini_dir:
        return Path(gemini_dir).resolve() / "antigravity" / DEFAULT_CONFIG_FILENAME
    return get_user_home() / ".gemini" / "antigravity" / DEFAULT_CONFIG_FILENAME


def get_default_config() -> Dict[str, Any]:
    """Returns the default blank configuration for custom models."""
    return {"version": 1, "providers": {}, "models": []}


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Loads custom models configuration from disk safely."""
    target_path = Path(path).resolve() if path else get_custom_models_path()
    if not target_path.is_file():
        return get_default_config()
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("providers", {})
                data.setdefault("models", [])
                return data
    except Exception:
        pass
    return get_default_config()


def save_config(config: Dict[str, Any], path: Optional[Path] = None) -> Path:
    """Saves custom models configuration safely using atomic write and 0o600 permissions."""
    target_path = Path(path).resolve() if path else get_custom_models_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.parent / f".{target_path.name}.tmp.{os.getpid()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, target_path)
        os.chmod(target_path, 0o600)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
    return target_path
