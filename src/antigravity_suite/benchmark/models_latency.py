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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "step_type": self.step_type,
            "source": self.source,
            "delta_sec": self.delta_sec,
            "timestamp": self.timestamp,
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
    steps: List[StepIntervalMetric] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_index": self.message_index,
            "user_step_index": self.user_step_index,
            "timestamp": self.timestamp,
            "prompt_preview": self.prompt_preview,
            "ttft_sec": self.ttft_sec,
            "total_duration_sec": self.total_duration_sec,
            "step_count": self.step_count,
            "avg_interval_sec": self.avg_interval_sec,
            "max_interval_sec": self.max_interval_sec,
            "max_interval_step": self.max_interval_step,
            "steps": [s.to_dict() for s in self.steps],
        }
