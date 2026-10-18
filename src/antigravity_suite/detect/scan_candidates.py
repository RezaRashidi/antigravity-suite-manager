"""
Candidate directory discovery across roots, PATH, and desktop files.
"""

from __future__ import annotations

import glob
import os
import shlex
from typing import Set

from antigravity_suite.detect.constants import PATHS_CONF
from antigravity_suite.detect.process import get_running_paths


def get_scan_candidates() -> Set[str]:
    cands: Set[str] = set()
    roots = [
        "/opt", "/usr/share", "/usr/lib", "/usr/local/share",
        os.path.expanduser("~/.local/share"), os.path.expanduser("~/.local/lib"),
        os.path.expanduser("~/opt"), os.path.expanduser("~/.antigravity"),
    ]
    for r in roots:
        if os.path.isdir(r):
            for pat in ["*antigravity*", "*Antigravity*"]:
                for m in glob.glob(os.path.join(r, pat)):
                    if os.path.isdir(m):
                        cands.add(os.path.realpath(m))

    if os.path.isfile(PATHS_CONF):
        try:
            with open(PATHS_CONF, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        v = v.strip().strip('"').strip("'")
                        if v and k in ["CUSTOM_PATHS", "CUSTOM_ANTIGRAVITY_PATHS"]:
                            for cp in v.split(":"):
                                if cp.strip() and os.path.isdir(os.path.expanduser(cp.strip())):
                                    cands.add(os.path.realpath(os.path.expanduser(cp.strip())))
                        elif v and k in ["APP_INSTALL_DIR", "IDE_INSTALL_DIR"]:
                            if os.path.isdir(os.path.expanduser(v)):
                                cands.add(os.path.realpath(os.path.expanduser(v)))
        except Exception:
            pass

    for p in os.environ.get("PATH", "").split(":"):
        for cmd in ["antigravity", "antigravity-ide", "antigravity-1", "antigravity-acc2"]:
            fp = os.path.join(p, cmd)
            if os.path.isfile(fp):
                rp = os.path.realpath(fp)
                d = os.path.dirname(rp)
                if "manager" not in d.lower():
                    cands.add(d)
                if os.path.basename(d) in ["bin", "MacOS"]:
                    cands.add(os.path.dirname(d))

    for ddir in [os.path.expanduser("~/.local/share/applications"), "/usr/share/applications"]:
        if os.path.isdir(ddir):
            for df in glob.glob(os.path.join(ddir, "*antigravity*.desktop")) + glob.glob(os.path.join(ddir, "*Antigravity*.desktop")):
                if "manager" not in df.lower():
                    try:
                        with open(df, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                if line.startswith("Exec="):
                                    cmd = (shlex.split(line.split("=", 1)[1].strip()) or [""])[0]
                                    if os.path.isfile(cmd):
                                        rp = os.path.realpath(cmd)
                                        d = os.path.dirname(rp)
                                        if "manager" not in d.lower():
                                            cands.add(d)
                                        if os.path.basename(d) == "bin":
                                            cands.add(os.path.dirname(d))
                    except Exception:
                        pass

    for rp in get_running_paths():
        if "manager" not in rp.lower():
            d = os.path.dirname(rp)
            cands.add(d)
            if os.path.basename(d) == "bin":
                cands.add(os.path.dirname(d))
    return cands
