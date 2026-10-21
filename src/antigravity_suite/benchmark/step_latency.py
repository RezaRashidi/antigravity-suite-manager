"""
Extracts message response latency, step intervals, and token/byte volumes from transcripts.
"""

from __future__ import annotations

import glob, json, os, re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models_latency import MessageTurnMetric, StepIntervalMetric


def find_latest_transcript(preferred: Optional[str] = None) -> Optional[Path]:
    if preferred and os.path.isfile(preferred):
        return Path(preferred)
    roots = [os.path.expanduser("~/.gemini/antigravity/brain"), os.path.expanduser("~/.config/Antigravity/brain")]
    cands: List[str] = []
    for r in roots:
        if os.path.isdir(r):
            cands.extend(glob.glob(os.path.join(r, "*", ".system_generated", "logs", "transcript*.jsonl")))
    valid = [p for p in cands if os.path.isfile(p) and os.path.getsize(p) > 0]
    return Path(max(valid, key=os.path.getmtime)) if valid else None


def parse_iso(ts_val: Optional[str]) -> Optional[datetime]:
    if not ts_val: return None
    try: return datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", str(ts_val).strip().replace("Z", "+00:00")))
    except Exception: return None


def _read_tail_entries(fpath: Path, max_bytes: int = 8 * 1024 * 1024) -> List[dict]:
    fsize = fpath.stat().st_size
    chunk = min(fsize, max_bytes)
    with open(fpath, "rb") as f:
        f.seek(fsize - chunk)
        lines = f.read(chunk).decode("utf-8", errors="ignore").splitlines()
    if fsize > chunk and lines: lines.pop(0)
    entries: List[dict] = []
    for l in lines:
        s = l.strip()
        if s.startswith("{") and s.endswith("}"):
            try: entries.append(json.loads(s))
            except Exception: pass
    return entries


def collect_recent_message_latencies(count: int = 10, transcript_path: Optional[str] = None) -> List[MessageTurnMetric]:
    t_file = find_latest_transcript(transcript_path)
    if not t_file:
        return []
    messages, cur = [], None
    for e in _read_tail_entries(t_file):
        stype, src = e.get("type"), e.get("source")
        if stype == "USER_INPUT" or src == "USER_EXPLICIT":
            if cur: messages.append(cur)
            raw = re.sub(r"<ADDITIONAL_METADATA>.*?</ADDITIONAL_METADATA>", "", str(e.get("content") or ""), flags=re.DOTALL)
            raw = re.sub(r"</?USER_REQUEST>", "", raw).strip()
            cur = {"idx": e.get("step_index") or 0, "ts": e.get("created_at") or "", "content": raw, "in_c": len(raw), "in_b": len(raw.encode("utf-8")), "steps": []}
        elif cur is not None:
            cur["steps"].append(e)
    if cur: messages.append(cur)

    results: List[MessageTurnMetric] = []
    for i, m in enumerate(messages[-count:], 1):
        t0 = parse_iso(m["ts"])
        ttft, t_prev, s_metrics = None, t0, []
        p_tok = next((int(s.get("input_tokens") or 0) for s in m["steps"] if s.get("input_tokens")), 0)
        for s in m["steps"]:
            t_cur = parse_iso(s.get("created_at"))
            delta = max(0.0, (t_cur - t_prev).total_seconds()) if (t_cur and t_prev) else 0.0
            if ttft is None and t0 and t_cur:
                ttft = max(0.0, (t_cur - t0).total_seconds())
            ot = int(s.get("output_tokens") or 0)
            ob = len((s.get("content") or "").encode("utf-8")) + len((s.get("thinking") or "").encode("utf-8"))
            s_metrics.append(StepIntervalMetric(s.get("step_index") or 0, s.get("type") or "STEP", s.get("source") or "", round(delta, 2), s.get("created_at") or "", ot, ob))
            if t_cur: t_prev = t_cur
        dur = max(0.0, (t_prev - t0).total_seconds()) if (m["steps"] and t0 and t_prev) else 0.0
        tot_tok = sum(s.output_tokens for s in s_metrics); tot_bytes = sum(s.output_bytes for s in s_metrics)
        tps = round(tot_tok / dur, 1) if (dur > 0 and tot_tok > 0) else 0.0
        intervals = [s.delta_sec for s in s_metrics]
        avg_int = round(sum(intervals) / len(intervals), 2) if intervals else 0.0; max_int = max(intervals) if intervals else 0.0
        max_step = s_metrics[intervals.index(max_int)].step_index if intervals else None
        p_prev = " ".join(m["content"].split())[:80] or "(empty prompt)"
        results.append(MessageTurnMetric(
            i, m["idx"], m["ts"], p_prev, round(ttft, 2) if ttft is not None else None,
            round(dur, 2) if dur else None, len(s_metrics), avg_int, max_int, max_step,
            m["in_c"], m["in_b"], p_tok, tot_tok, tot_bytes, tps, s_metrics,
        ))
    return results
