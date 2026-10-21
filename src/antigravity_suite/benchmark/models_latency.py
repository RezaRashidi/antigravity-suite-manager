"""
Data models for message turn and step interval telemetry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StepIntervalMetric:
    step_index: int
    step_type: str
    source: str
    delta_sec: float
    timestamp: str
    output_tokens: int = 0
    output_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index, "step_type": self.step_type, "source": self.source,
            "delta_sec": self.delta_sec, "timestamp": self.timestamp,
            "output_tokens": self.output_tokens, "output_bytes": self.output_bytes,
        }


@dataclass
class MessageTurnMetric:
    message_index: int
    user_step_index: int
    timestamp: str
    prompt_preview: str
    ttft_sec: Optional[float] = None
    total_duration_sec: Optional[float] = None
    step_count: int = 0
    avg_interval_sec: float = 0.0
    max_interval_sec: float = 0.0
    max_interval_step: Optional[int] = None
    input_chars: int = 0
    input_bytes: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    output_bytes: int = 0
    tokens_per_sec: float = 0.0
    steps: List[StepIntervalMetric] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_index": self.message_index, "user_step_index": self.user_step_index,
            "timestamp": self.timestamp, "prompt_preview": self.prompt_preview,
            "ttft_sec": self.ttft_sec, "total_duration_sec": self.total_duration_sec,
            "step_count": self.step_count, "avg_interval_sec": self.avg_interval_sec,
            "max_interval_sec": self.max_interval_sec, "max_interval_step": self.max_interval_step,
            "input_chars": self.input_chars, "input_bytes": self.input_bytes,
            "prompt_tokens": self.prompt_tokens, "output_tokens": self.output_tokens,
            "output_bytes": self.output_bytes, "tokens_per_sec": self.tokens_per_sec,
            "steps": [s.to_dict() for s in self.steps],
        }
