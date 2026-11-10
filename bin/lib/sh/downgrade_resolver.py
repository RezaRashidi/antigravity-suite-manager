#!/usr/bin/env python3
"""
Release discovery and version resolution helper for Antigravity App and IDE downgrades.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


def normalize_version(ver: str) -> str:
    ver = (ver or "").strip()
    if ver.lower().startswith("v"):
        ver = ver[1:]
    return ver.strip()


def version_tuple(ver: str) -> List[Any]:
    norm = normalize_version(ver)
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", norm)]


def get_releases(comp: str, cache_dir: str = "/tmp/antigravity-cache") -> List[Dict[str, Any]]:
    comp = comp.lower().strip()
    releases: Dict[str, Dict[str, Any]] = {}

    if comp in ["app", "antigravity-app"]:
        api_url = "https://antigravity-hub-auto-updater-974169037036.us-central1.run.app/releases"
        tmpl = "https://storage.googleapis.com/antigravity-public/antigravity-hub/{ver}-{eid}/linux-x64/Antigravity.tar.gz"
        pkg_prefix = "Antigravity-App-"
    elif comp in ["ide", "antigravity-ide"]:
        api_url = "https://antigravity-ide-auto-updater-974169037036.us-central1.run.app/releases"
        tmpl = "https://edgedl.me.gvt1.com/edgedl/release2/j0qc3/antigravity/stable/{ver}-{eid}/linux-x64/Antigravity%20IDE.tar.gz"
        pkg_prefix = "Antigravity-IDE-"
    else:
        return []

    # 1. Fetch remote release list from official Google updater endpoint
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Antigravity-Suite-Manager"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                for item in data:
                    v = normalize_version(item.get("version", ""))
                    eid = item.get("execution_id")
                    if v and eid:
                        url = tmpl.format(ver=v, eid=eid)
                        releases[v] = {
                            "version": v,
                            "execution_id": eid,
                            "url": url,
                            "cached": False,
                            "cache_path": None,
                        }
    except Exception:
        # Offline or remote endpoint unreachable; gracefully rely on local cache
        pass

    # 2. Inspect local archive cache for pre-downloaded versions
    cache_dir = os.path.expanduser(cache_dir)
    if os.path.isdir(cache_dir):
        pattern = os.path.join(cache_dir, f"{pkg_prefix}*.tar.gz")
        for f in glob.glob(pattern):
            base = os.path.basename(f)
            m = re.search(re.escape(pkg_prefix) + r"([0-9.]+)\.tar\.gz", base)
            if m:
                cver = normalize_version(m.group(1))
                if cver in releases:
                    releases[cver]["cached"] = True
                    releases[cver]["cache_path"] = f
                else:
                    releases[cver] = {
                        "version": cver,
                        "execution_id": None,
                        "url": f,
                        "cached": True,
                        "cache_path": f,
                    }

    # Sort releases descending by version
    sorted_vers = sorted(releases.keys(), key=version_tuple, reverse=True)
    return [releases[v] for v in sorted_vers]


def resolve_release(
    comp: str,
    target: str,
    current_ver: Optional[str] = None,
    cache_dir: str = "/tmp/antigravity-cache"
) -> Tuple[str, str]:
    comp = comp.lower().strip()
    target = (target or "").strip()
    norm_cur = normalize_version(current_ver or "")

    # Direct URL passed
    if target.startswith("http://") or target.startswith("https://"):
        m = re.search(r"([0-9]+\.[0-9]+(?:\.[0-9]+)?)", target)
        ver = m.group(1) if m else "Custom"
        return ver, target

    releases = get_releases(comp, cache_dir)
    releases_map = {r["version"]: r for r in releases}

    # Relative target: 'prev', 'previous', 'prior'
    if target.lower() in ["prev", "previous", "prior"]:
        if norm_cur and norm_cur in releases_map:
            cur_idx = next(i for i, r in enumerate(releases) if r["version"] == norm_cur)
            if cur_idx + 1 < len(releases):
                older = releases[cur_idx + 1]
                return older["version"], older["url"]
        elif len(releases) > 1:
            return releases[1]["version"], releases[1]["url"]

    # Target: 'latest'
    if target.lower() == "latest" and releases:
        return releases[0]["version"], releases[0]["url"]

    norm_target = normalize_version(target)
    if norm_target in releases_map:
        item = releases_map[norm_target]
        return item["version"], item["url"]

    # Check cache directly if not found in remote map
    pkg_prefix = "Antigravity-App-" if comp in ["app", "antigravity-app"] else "Antigravity-IDE-"
    cache_file = os.path.join(cache_dir, f"{pkg_prefix}{norm_target}.tar.gz")
    if os.path.isfile(cache_file):
        return norm_target, cache_file

    # Fallback if unknown
    return norm_target, ""


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: downgrade_resolver.py <list|resolve> <app|ide> [args...]", file=sys.stderr)
        sys.exit(1)

    action = sys.argv[1].lower()

    if action == "list":
        comp = sys.argv[2] if len(sys.argv) > 2 else "app"
        cache_dir = sys.argv[3] if len(sys.argv) > 3 else "/tmp/antigravity-cache"
        releases = get_releases(comp, cache_dir)
        for r in releases:
            cached_flag = "1" if r["cached"] else "0"
            print(f"{r['version']}|{r['url']}|{cached_flag}")
        sys.exit(0)

    elif action == "resolve":
        comp = sys.argv[2] if len(sys.argv) > 2 else "app"
        target = sys.argv[3] if len(sys.argv) > 3 else ""
        current_ver = sys.argv[4] if len(sys.argv) > 4 else ""
        cache_dir = sys.argv[5] if len(sys.argv) > 5 else "/tmp/antigravity-cache"

        ver, url = resolve_release(comp, target, current_ver, cache_dir)
        if not ver or not url:
            print(f"Error: Unable to resolve release for {comp} target '{target}'", file=sys.stderr)
            sys.exit(1)
        print(f"{ver}|{url}")
        sys.exit(0)

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
