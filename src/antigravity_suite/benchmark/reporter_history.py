"""
Formatters for message volume clustering, throughput, and compact interaction telemetry.
"""

from __future__ import annotations

from typing import Dict, List
from .models_latency import MessageTurnMetric

_BOLD, _RESET = "\033[1m", "\033[0m"
_GREEN, _YELLOW, _RED, _CYAN, _DIM = "\033[92m", "\033[93m", "\033[91m", "\033[96m", "\033[2m"


def _col(sec: float | None) -> str:
    if sec is None: return f"{_DIM}  n/a{_RESET}"
    c = _GREEN if sec < 2.0 else (_YELLOW if sec < 8.0 else _RED)
    return f"{c}{sec:4.1f}s{_RESET}"


def _fmt_kb(b: int) -> str:
    return f"{b / 1024:.1f} KB" if b >= 1024 else f"{b} B"


def _tier(m: MessageTurnMetric) -> str:
    return "Light (<5k)" if m.output_tokens < 5000 else ("Medium (5-30k)" if m.output_tokens <= 30000 else "Heavy (>30k)")


def _cluster_summary(messages: List[MessageTurnMetric]) -> List[str]:
    lines = [f"\n{_BOLD}Volume Cluster Performance Analysis:{_RESET}"]
    clusters: Dict[str, List[MessageTurnMetric]] = {}
    for m in messages: clusters.setdefault(_tier(m), []).append(m)
    for c_name in ["Light (<5k)", "Medium (5-30k)", "Heavy (>30k)"]:
        grp = clusters.get(c_name, [])
        if not grp: continue
        avg_ttft = sum(m.ttft_sec or 0.0 for m in grp) / len(grp)
        avg_dur = sum(m.total_duration_sec or 0.0 for m in grp) / len(grp)
        spds = [m.tokens_per_sec for m in grp if m.tokens_per_sec > 0]
        avg_spd = sum(spds) / len(spds) if spds else 0.0
        avg_in, avg_out = sum(m.input_chars for m in grp) // len(grp), sum(m.output_tokens for m in grp) // len(grp)
        lines.append(f"  • {c_name:<16} [{len(grp):2d} msgs]: Avg TTFT: {_col(avg_ttft)} | Avg Dur: {avg_dur:6.1f}s | Speed: {avg_spd:5.1f} tok/s | In: {avg_in:3d} c | Out: {avg_out:6,d} tok")
    return lines


def _compact_table(messages: List[MessageTurnMetric]) -> List[str]:
    lines = [f"\n{_BOLD}Recent Interactions (Last {len(messages)} Messages):{_RESET}"]
    lines.append(f"{_DIM}{'Time':<5} | {'Tier':<6} | {'Input (c / ctx)':<15} | {'Output (tok / KB)':<18} | {'TTFT':<5} | {'Dur':<6} | {'Speed':<9} | {'Prompt'}{_RESET}")
    lines.append(f"{_DIM}{'-' * 98}{_RESET}")
    for m in messages:
        t_str = m.timestamp[11:16] if len(m.timestamp) >= 16 else "--:--"
        tier_s = _tier(m).split()[0]
        in_s = f"{m.input_chars}c / {m.prompt_tokens // 1000}k" if m.prompt_tokens >= 1000 else f"{m.input_chars}c / {m.prompt_tokens}t"
        tok_s = f"{m.output_tokens // 1000}k" if m.output_tokens >= 1000 else f"{m.output_tokens}t"
        out_s = f"{tok_s} ({_fmt_kb(m.output_bytes)})"
        dur_s = f"{m.total_duration_sec:.0f}s" if m.total_duration_sec is not None else "n/a"
        spd_s = f"{m.tokens_per_sec:.1f} t/s" if m.tokens_per_sec > 0 else "n/a"
        p_sub = (m.prompt_preview[:24] + "..") if len(m.prompt_preview) > 24 else m.prompt_preview
        lines.append(f"{t_str:<5} | {tier_s:<6} | {in_s:<15} | {out_s:<18} | {_col(m.ttft_sec)} | {dur_s:<6} | {spd_s:<9} | \"{p_sub}\"")
    return lines


def format_recent_messages_section(messages: List[MessageTurnMetric], all_steps: bool = False) -> List[str]:
    if not messages:
        return [f"\n{_BOLD}Recent Interaction Performance & Volume Clustering:{_RESET}\n  {_DIM}(No recent conversation transcript history located){_RESET}"]

    lines = [f"\n{_BOLD}=== Recent Interaction Performance & Volume Clustering ==={_RESET}"]
    lines.extend(_cluster_summary(messages))
    lines.extend(_compact_table(messages))

    tot_in_c = sum(m.input_chars for m in messages); tot_out_tok = sum(m.output_tokens for m in messages)
    tot_out_b = sum(m.output_bytes for m in messages)
    spds = [m.tokens_per_sec for m in messages if m.tokens_per_sec > 0]
    avg_s = sum(spds) / len(spds) if spds else 0.0
    lines.append(f"\n{_BOLD}Aggregate Volume:{_RESET} Input: {tot_in_c:,} chars | Output: {tot_out_tok:,} tokens ({tot_out_b / 1024:.1f} KB) across {len(messages)} msgs | Avg Speed: {avg_s:.1f} tok/s")

    if all_steps:
        lines.append(f"\n{_BOLD}Expanded Step Timelines (--all-steps):{_RESET}")
        for m in messages:
            lines.append(f"  [{m.timestamp[11:16]}] Msg {m.user_step_index} ({len(m.steps)} steps, {m.output_tokens} tok):")
            for s in m.steps:
                lines.append(f"    -> Step {s.step_index:<5} [{s.step_type:<16}] {_col(s.delta_sec)} ({s.output_tokens} tok, {s.output_bytes} B)")
    return lines
