"""Parser for remote model catalog payloads (OpenAI, Ollama, raw lists)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

VISION_KEYWORDS = {"vision", "vl", "omni", "gpt-4o", "llava", "mllama", "clip"}
THINKING_KEYWORDS = {"thinking", "reasoning", "deepseek-r1", "qwq", "o1", "o3"}


@dataclass
class ModelInfo:
    id: str
    name: str
    context_length: Optional[int] = None
    max_output_tokens: Optional[int] = None
    capabilities: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "context_length": self.context_length,
            "max_output_tokens": self.max_output_tokens,
            "capabilities": dict(self.capabilities),
        }


def _detect_capabilities(item: Dict[str, Any], text: str) -> Dict[str, bool]:
    explicit = item.get("capabilities", {})
    details = item.get("details", {})
    families = [str(f).lower() for f in details.get("families", [])]
    vis = bool(explicit.get("vision")) or any(k in text for k in VISION_KEYWORDS)
    vis = vis or any("clip" in f or "mllama" in f for f in families)
    think = bool(explicit.get("thinking") or explicit.get("reasoning"))
    think = think or any(re.search(rf"\b{k}\b", text) or k in text for k in THINKING_KEYWORDS)
    return {"vision": vis, "thinking": think}


def _extract_context_length(item: Dict[str, Any], text: str) -> Optional[int]:
    for key in ("context_length", "context_window", "max_context_length"):
        if key in item and isinstance(item[key], int):
            return item[key]
    if "details" in item and "context_length" in item["details"]:
        return item["details"]["context_length"]
    match = re.search(r"(\d+)k", text)
    if match:
        return int(match.group(1)) * 1024
    return None


def parse_model_catalog(data: Any) -> List[ModelInfo]:
    """Parses catalog responses into structured ModelInfo instances."""
    items: List[Dict[str, Any]] = []
    if isinstance(data, list):
        items = [x for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        if isinstance(data.get("data"), list):
            items = [x for x in data["data"] if isinstance(x, dict)]
        elif isinstance(data.get("models"), list):
            items = [x for x in data["models"] if isinstance(x, dict)]

    results: List[ModelInfo] = []
    for it in items:
        mid = str(it.get("id") or it.get("model") or it.get("name") or "").strip()
        if not mid:
            continue
        name = str(it.get("name") or mid)
        search_text = f"{mid} {name}".lower()
        ctx_len = _extract_context_length(it, search_text)
        max_out = it.get("max_output_tokens") or it.get("max_tokens")
        caps = _detect_capabilities(it, search_text)
        results.append(
            ModelInfo(
                id=mid,
                name=name,
                context_length=ctx_len,
                max_output_tokens=max_out if isinstance(max_out, int) else None,
                capabilities=caps,
            )
        )
    return results
