"""
Sync Manifest and Tombstone Persistence.
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, Set

MANIFEST_FILENAME = "sync_manifest.json"


def get_manifest_path(effective_master: Path) -> Path:
    """Returns the canonical path to the sync manifest JSON file."""
    return effective_master / MANIFEST_FILENAME


def load_manifest(effective_master: Path) -> Dict[str, Any]:
    """Loads the synchronization manifest tracking known conversations and tombstones."""
    m_path = get_manifest_path(effective_master)
    default = {
        "version": 2, "known_ids": [], "known_app_ids": [],
        "known_ide_ids": [], "tombstones": {}, "last_synced_at": "",
    }
    if not m_path.is_file():
        return default
    try:
        with open(m_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return default
            data.setdefault("version", 2)
            data.setdefault("known_ids", [])
            data.setdefault("known_app_ids", list(data.get("known_ids", [])))
            data.setdefault("known_ide_ids", list(data.get("known_ids", [])))
            data.setdefault("tombstones", {})
            return data
    except Exception:
        return default


def save_manifest(effective_master: Path, manifest: Dict[str, Any]) -> None:
    """Atomically saves the synchronization manifest to disk."""
    m_path = get_manifest_path(effective_master)
    manifest["version"] = 2
    manifest["last_synced_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tmp_path = m_path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, m_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def get_tombstones(effective_master: Path) -> Set[str]:
    """Retrieves the set of all deleted conversation UUIDs from the manifest."""
    return set(load_manifest(effective_master).get("tombstones", {}).keys())
