"""
Formatters for recent message response latencies, step intervals, and volume telemetry.
"""

from __future__ import annotations

from typing import List
from .models_latency import MessageTurnMetric

_BOLD, _RESET = "\033[1m", "\033[0m"
_GREEN, _YELLOW, _RED, _CYAN, _DIM = "\033[92m", "\033[93m", "\033[91m", "\033[96m", "\033[2m"


def _col_delta(sec: float) -> str:
    c = _GREEN if sec < 2.0 else (_YELLOW if sec < 8.0 else _RED)
    return f"{c}+{sec:.2f}s{_RESET}"


def _fmt_step(s) -> str:
    vol = f"({s.output_tokens} tok, {s.output_bytes / 1024:.1f} KB)" if s.output_tokens else f"({s.output_bytes} B)"
    return f"    -> Step {s.step_index:<5} [{s.step_type:<16} | {s.source:<5}] {_col_delta(s.delta_sec):<18} {vol:<16} (@ {s.timestamp})"


def format_recent_messages_section(messages: List[MessageTurnMetric], all_steps: bool = False) -> List[str]:
    lines = [f"\n{_BOLD}Recent Message Telemetry & Step Intervals (Last {len(messages)} Messages):{_RESET}"]
    if not messages:
        lines.append(f"  {_DIM}(No recent conversation transcript history located){_RESET}")
        return lines

    for m in messages:
        lines.append(f"\n{_CYAN}─── [Message {m.message_index:02d}/{len(messages):02d}] ────────────────────────────────────────────────────────{_RESET}")
        lines.append(f"  {_BOLD}Prompt Step{_RESET}    : {m.user_step_index} @ {m.timestamp}")
        lines.append(f"  {_BOLD}User Prompt{_RESET}    : \"{m.prompt_preview}\"")

        p_ctx = f" | Model Context: ~{m.prompt_tokens:,} tokens" if m.prompt_tokens else ""
        lines.append(f"  {_BOLD}Input Volume{_RESET}   : {m.input_chars:,} chars ({m.input_bytes / 1024:.1f} KB){p_ctx}")

        tps_str = f" | Velocity: {m.tokens_per_sec:.1f} tok/s" if m.tokens_per_sec > 0 else ""
        lines.append(f"  {_BOLD}Output Volume{_RESET}  : {m.output_tokens:,} tokens | {m.output_bytes / 1024:.1f} KB across {m.step_count} step(s){tps_str}")

        ttft_str = f"{_col_delta(m.ttft_sec)} (Initial Model Response)" if m.ttft_sec is not None else f"{_DIM}n/a{_RESET}"
        lines.append(f"  {_BOLD}Response (TTFT){_RESET}: {ttft_str}")

        dur_str = f"{m.total_duration_sec:.2f}s" if m.total_duration_sec is not None else "n/a"
        slow_str = f"Slowest: Step {m.max_interval_step} [{_col_delta(m.max_interval_sec)}]" if m.max_interval_step else "none"
        lines.append(f"  {_BOLD}Turn Duration{_RESET}  : {dur_str} (Avg step: {m.avg_interval_sec:.2f}s | {slow_str})")

        if not m.steps:
            continue
        lines.append(f"  {_BOLD}Step Timeline{_RESET}  :")
        if len(m.steps) <= 10 or all_steps:
            for s in m.steps: lines.append(_fmt_step(s))
        else:
            for s in m.steps[:3]: lines.append(_fmt_step(s))
            hidden = len(m.steps) - 5
            lines.append(f"       {_DIM}... [{hidden} intermediate steps hidden - pass --all-steps to view full timeline] ...{_RESET}")
            slowest = sorted(m.steps, key=lambda x: x.delta_sec, reverse=True)[:3]
            lines.append(f"       {_YELLOW}[!] Slowest Gaps:{_RESET}")
            for sl in slowest:
                lines.append(f"           • Step {sl.step_index} [{sl.step_type}]: {_col_delta(sl.delta_sec)} ({sl.output_tokens} tok)")
            for s in m.steps[-2:]: lines.append(_fmt_step(s))

    if len(messages) > 1:
        tot_in_c = sum(m.input_chars for m in messages); tot_in_b = sum(m.input_bytes for m in messages)
        tot_out_tok = sum(m.output_tokens for m in messages); tot_out_b = sum(m.output_bytes for m in messages)
        t_speeds = [m.tokens_per_sec for m in messages if m.tokens_per_sec > 0]
        avg_speed = sum(t_speeds) / len(t_speeds) if t_speeds else 0.0
        lines.append(f"\n{_BOLD}Aggregate Volume Summary ({len(messages)} Messages):{_RESET}")
        lines.append(f"  • Total Input  : {tot_in_c:,} chars ({tot_in_b / 1024:.1f} KB) | Avg: {tot_in_c // len(messages):,} chars/msg")
        lines.append(f"  • Total Output : {tot_out_tok:,} tokens ({tot_out_b / 1024:.1f} KB) | Avg: {tot_out_tok // len(messages):,} tok/msg")
        if avg_speed > 0: lines.append(f"  • Generation   : ~{avg_speed:.1f} tokens/second average throughput")
    return lines
