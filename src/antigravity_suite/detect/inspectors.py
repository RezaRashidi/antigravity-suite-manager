"""
Directory inspectors for Antigravity App and IDE installations.
"""

from __future__ import annotations

import json
import os
import re
import struct
from typing import Any, Dict, Optional


def inspect_app_dir(d: str) -> Optional[Dict[str, Any]]:
    if "manager" in d.lower():
        return None
    asar = os.path.join(d, "resources", "app.asar")
    if not os.path.isfile(asar):
        return None
    ver = "Unknown"
    try:
        with open(asar, "rb") as f:
            magic, h_s, h_o, j_len = struct.unpack("<IIII", f.read(16))
            hdr = json.loads(f.read(j_len).decode("utf-8"))
            curr = hdr.get("files", {}).get("package.json", {})
            if "offset" in curr and "size" in curr:
                f.seek(8 + h_s + int(curr["offset"]))
                pkg_raw = f.read(int(curr["size"])).decode("utf-8", errors="ignore")
                try:
                    ver = str(json.loads(pkg_raw).get("version", ver))
                except Exception:
                    m = re.search(r'"version"\s*:\s*"([^"]+)"', pkg_raw)
                    if m:
                        ver = m.group(1)
    except Exception:
        pass

    exe = None
    for name in ["antigravity", "antigravity-app"]:
        p = os.path.join(d, name)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            exe = p
            break
    if not exe:
        for f in os.listdir(d):
            if f.startswith("antigravity") and "manager" not in f and os.access(os.path.join(d, f), os.X_OK):
                exe = os.path.join(d, f)
                break
    if not exe or "manager" in exe.lower():
        return None

    res_dir = os.path.join(d, "resources")
    writable = os.access(d, os.W_OK) and (not os.path.isdir(res_dir) or os.access(res_dir, os.W_OK))
    return {"type": "Antigravity App", "version": ver, "path": d, "executable": exe, "writable": writable}


def inspect_ide_dir(d: str) -> Optional[Dict[str, Any]]:
    prod = os.path.join(d, "resources", "app", "product.json")
    pkg = os.path.join(d, "resources", "app", "package.json")
    if not (os.path.isfile(prod) or os.path.isfile(pkg)):
        return None
    ver = "Unknown"
    try:
        if os.path.isfile(prod):
            with open(prod, "r", encoding="utf-8") as f:
                data = json.load(f)
                ver = data.get("ideVersion") or data.get("version") or ver
        if ver == "Unknown" and os.path.isfile(pkg):
            with open(pkg, "r", encoding="utf-8") as f:
                data = json.load(f)
                ver = data.get("version") or ver
    except Exception:
        pass

    exe = None
    for rel in ["antigravity-ide", "bin/antigravity-ide", "code"]:
        p = os.path.join(d, rel)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            exe = p
            break

    res_dir = os.path.join(d, "resources")
    writable = os.access(d, os.W_OK) and (not os.path.isdir(res_dir) or os.access(res_dir, os.W_OK))
    return {"type": "Antigravity IDE", "version": ver, "path": d, "executable": exe, "writable": writable}
