"""ANSI table & ASCII bar renderer for Antigravity Token Usage & Cost Report."""

from __future__ import annotations

from typing import Any, Dict

from antigravity_suite.detect.constants import BLUE, BOLD, CYAN, GREEN, NC, YELLOW


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_usd(v: float) -> str:
    if v >= 100.0:
        return f"${v:,.2f}"
    if v >= 1.0:
        return f"${v:.2f}"
    return f"${v:.4f}"


def render_usage_report(data: Dict[str, Any], max_days: int = 14) -> str:
    lines = []
    scope = f"Last {data['filter_days']} days" if data.get("filter_days") else "All recorded history"
    lines.append(f"\n{CYAN}========================================================================================{NC}")
    lines.append(f"{BOLD}{CYAN}               Antigravity Suite — Token Usage & Cost Report ({scope}){NC}")
    lines.append(f"{CYAN}========================================================================================{NC}")
    lines.append(
        f"  Scanned: {BOLD}{data['files_scanned']}{NC} transcripts | Active Cascades: {BOLD}{data['cascades_with_usage']}{NC} | "
        f"Active Days: {BOLD}{data['active_days']}{NC} | Pricing: {GREEN}{data['pricing_source']}{NC}"
    )

    lines.append(f"\n{BOLD}{BLUE}[ TIME WINDOWS ]{NC}")
    lines.append(f"  {'Window':<10} {'Turns':>7} {'Input':>10} {'Cache Read':>12} {'Output':>10} {'Cache Hit':>10} {'Cost (USD)':>12} {'Saved':>10}")
    lines.append("  " + "-" * 85)
    for label, key in (("Today", "today"), ("7 Days", "7d"), ("30 Days", "30d"), ("All Time", "all")):
        w = data["windows"][key]
        lines.append(
            f"  {label:<10} {w['turns']:>7} {fmt_tokens(w['input_tokens']):>10} {fmt_tokens(w['cache_read_tokens']):>12} "
            f"{fmt_tokens(w['output_tokens']):>10} {w['cache_hit_rate']:>9.1f}% {fmt_usd(w['cost_usd']):>12} {GREEN}{fmt_usd(w['cache_savings_usd']):>10}{NC}"
        )

    lines.append(f"\n{BOLD}{BLUE}[ BY ACCOUNT ]{NC}")
    if data["by_account"]:
        lines.append(f"  {'Account':<34} {'Turns':>6} {'Input':>9} {'Cache Rd':>10} {'Output':>9} {'Hit%':>7} {'Cost':>10}")
        lines.append("  " + "-" * 85)
        for row in data["by_account"]:
            acct = row["account"]
            if len(acct) > 33:
                acct = acct[:30] + "..."
            lines.append(
                f"  {acct:<34} {row['turns']:>6} {fmt_tokens(row['input_tokens']):>9} {fmt_tokens(row['cache_read_tokens']):>10} "
                f"{fmt_tokens(row['output_tokens']):>9} {row['cache_hit_rate']:>6.1f}% {YELLOW}{fmt_usd(row['cost_usd']):>10}{NC}"
            )
    else:
        lines.append("  No token usage rows found for the selected filter.")

    lines.append(f"\n{BOLD}{BLUE}[ BY MODEL ]{NC}")
    if data["by_model"]:
        lines.append(f"  {'Model':<34} {'Turns':>6} {'Input':>9} {'Cache Rd':>10} {'Output':>9} {'Hit%':>7} {'Cost':>10}")
        lines.append("  " + "-" * 85)
        for row in data["by_model"]:
            mod = row["model"]
            if len(mod) > 33:
                mod = mod[:30] + "..."
            lines.append(
                f"  {mod:<34} {row['turns']:>6} {fmt_tokens(row['input_tokens']):>9} {fmt_tokens(row['cache_read_tokens']):>10} "
                f"{fmt_tokens(row['output_tokens']):>9} {row['cache_hit_rate']:>6.1f}% {YELLOW}{fmt_usd(row['cost_usd']):>10}{NC}"
            )

    recent_days = data["by_day"][-max_days:]
    if recent_days:
        lines.append(f"\n{BOLD}{BLUE}[ DAILY ACTIVITY (Last {len(recent_days)} Active Days) ]{NC}")
        max_tok = max(max(d["total_tokens"] for d in recent_days), 1)
        for d in recent_days:
            bar_len = max(1, int(round((d["total_tokens"] / max_tok) * 28)))
            bar = "#" * bar_len
            lines.append(
                f"  {d['date']}  {CYAN}{bar:<28}{NC}  {fmt_tokens(d['total_tokens']):>8}  ({d['turns']:>3} turns)  {fmt_usd(d['cost_usd']):>9}  Hit {d['cache_hit_rate']:>5.1f}%"
            )

    lines.append(f"{CYAN}========================================================================================{NC}")
    return "\n".join(lines)
