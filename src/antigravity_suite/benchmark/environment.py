"""
System environment, CPU, RAM, OS, versions, and proxy inspector.
"""

from __future__ import annotations

import os
import platform
from typing import Dict, Tuple

from antigravity_suite.detect.scan import scan_installations
from .models_system import EnvironmentMetric


def _get_installed_versions() -> Tuple[str, str]:
    app_v, ide_v = "not installed", "not installed"
    try:
        installs = scan_installations()
        for item in installs:
            t = item.get("type", "")
            v = item.get("version", "unknown")
            p = item.get("path", "")
            if "App" in t and app_v == "not installed":
                app_v = f"v{v} ({p})"
            elif "IDE" in t and ide_v == "not installed":
                ide_v = f"v{v} ({p})"
    except Exception:
        pass
    return app_v, ide_v


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
    app_ver, ide_ver = _get_installed_versions()
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
        app_version=app_ver,
        ide_version=ide_ver,
        active_proxies=_get_active_proxies(),
    )
