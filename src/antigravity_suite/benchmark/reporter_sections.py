"""
Section formatters for benchmark environment, account quota, and prompt tests.
"""

from __future__ import annotations

from typing import List

from .models_system import AccountQuotaMetric, EnvironmentMetric, PromptTestMetric

_BOLD = "\033[1m"
_RESET = "\033[0m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"


def format_env_section(env: EnvironmentMetric) -> List[str]:
    lines = [f"\n{_BOLD}System & Environment Specifications:{_RESET}"]
    lines.append(f"  - OS & Kernel      : {env.os_name} (Kernel: {env.kernel})")
    lines.append(f"  - CPU Specs        : {env.cpu_model} ({env.cpu_cores} cores) | Load: {env.load_avg}")
    lines.append(f"  - Memory (RAM)     : {env.ram_avail_mb:.0f} MB avail / {env.ram_total_mb:.0f} MB total")
    lines.append(f"  - Antigravity Vers : App: {env.app_version} | IDE: {env.ide_version}")
    if env.active_proxies:
        p_strs = [f"{k}={v}" for k, v in env.active_proxies.items()]
        lines.append(f"  - Active Proxies   : {', '.join(p_strs)}")
    return lines


def format_account_section(accounts: List[AccountQuotaMetric]) -> List[str]:
    lines = [f"\n{_BOLD}Account Quotas & Server-Side Priority Tier:{_RESET}"]
    if not accounts:
        lines.append("  (No authenticated accounts or quota information found)")
        return lines

    for acc in accounts:
        tier_col = _GREEN if "PRO" in acc.tier.upper() or "ULTRA" in acc.tier.upper() else _YELLOW
        lines.append(
            f"  - User: {_BOLD}{acc.email or 'Active User'}{_RESET} | "
            f"Tier: {tier_col}{acc.tier}{_RESET} ({acc.source})"
        )
        if acc.region_code:
            lines.append(f"    Cloud Region     : {acc.region_code}")
        for b in acc.buckets:
            pct = b.remaining_fraction * 100
            pct_col = _GREEN if pct > 50 else (_YELLOW if pct > 20 else _RED)
            reset_note = f" (resets {b.reset_time})" if b.reset_time else ""
            lines.append(
                f"    Bucket [{b.window:6}] : {b.name:24} -> "
                f"{pct_col}{pct:5.1f}% remaining{_RESET}{reset_note}"
            )
    return lines


def format_prompt_test_section(pt: PromptTestMetric | None) -> List[str]:
    if not pt:
        return []
    lines = [f"\n{_BOLD}Live Model Response & Latency Test:{_RESET}"]
    if pt.success:
        lat_col = _GREEN if pt.latency_ms and pt.latency_ms < 1500 else _YELLOW
        lines.append(f"  - Test Probe       : {pt.prompt_text}")
        lines.append(f"  - End-to-End RTT   : {lat_col}{pt.latency_ms:.1f} ms{_RESET}")
        if pt.output_preview:
            lines.append(f"  - Sample Output    : \"{pt.output_preview}\"")
    else:
        lines.append(f"  - Status           : {_RED}FAILED{_RESET} ({pt.error})")
    return lines
