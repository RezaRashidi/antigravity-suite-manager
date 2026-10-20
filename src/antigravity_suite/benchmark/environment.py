"""
System environment, CPU, RAM, OS, versions, and proxy inspector.
"""

from __future__ import annotations

import os
import platform
import subprocess
from typing import Dict

from .models_system import EnvironmentMetric


def _get_antigravity_version(path: str) -> str:
    pkg = os.path.join(path, "resources", "app", "package.json")
    if os.path.isfile(pkg):
        try:
            import json
            with open(pkg, "r", encoding="utf-8") as f:
                return str(json.load(f).get("version", "unknown"))
        except Exception:
            pass
    ver_file = os.path.join(path, "version")
    if os.path.isfile(ver_file):
        try:
            with open(ver_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return "not installed"


def _get_cpu_model() -> str:
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "unknown"


def _get_ram_mb() -> tuple[float, float]:
    tot, avail = 0.0, 0.0
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    tot = float(line.split()[1]) / 1024.0
                elif line.startswith("MemAvailable:"):
                    avail = float(line.split()[1]) / 1024.0
    except Exception:
        pass
    return tot, avail


def _get_active_proxies() -> Dict[str, str]:
    proxies: Dict[str, str] = {}
    for var in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
        val = os.environ.get(var)
        if val:
            proxies[var.lower()] = val
    # Check IDE settings.json
    ide_settings = os.path.expanduser("~/.config/Antigravity IDE/User/settings.json")
    if os.path.isfile(ide_settings):
        try:
            import json
            with open(ide_settings, "r", encoding="utf-8") as f:
                p = json.load(f).get("http.proxy")
                if p:
                    proxies["ide_http_proxy"] = str(p)
        except Exception:
            pass
    return proxies


def collect_environment() -> EnvironmentMetric:
    tot_ram, avail_ram = _get_ram_mb()
    try:
        loads = os.getloadavg()
        load_str = f"{loads[0]:.2f}, {loads[1]:.2f}, {loads[2]:.2f}"
    except Exception:
        load_str = "n/a"

    return EnvironmentMetric(
        os_name=platform.platform(),
        kernel=platform.release(),
        cpu_model=_get_cpu_model(),
        cpu_cores=os.cpu_count() or 1,
        load_avg=load_str,
        ram_total_mb=round(tot_ram, 1),
        ram_avail_mb=round(avail_ram, 1),
        app_version=_get_antigravity_version("/opt/antigravity2"),
        ide_version=_get_antigravity_version("/opt/antigravity"),
        active_proxies=_get_active_proxies(),
    )
