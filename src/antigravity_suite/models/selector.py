"""Model selector and standard naming generator for Antigravity custom models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from antigravity_suite.models.parser import ModelInfo


def make_standard_name(provider: str, model_id: str) -> str:
    """Creates standard identifier formatted as models/{provider}-{model_id}."""
    prov = provider.strip().lower()
    mid = model_id.strip()
    prefix = f"models/{prov}-"
    if mid.startswith(prefix):
        return mid
    if mid.startswith("models/"):
        mid = mid[len("models/"):]
    return f"{prefix}{mid}"


def _model_to_dict(item: Any, provider: str, enabled: bool) -> Dict[str, Any]:
    mid = item.id if isinstance(item, ModelInfo) else str(item.get("id", ""))
    name = item.name if isinstance(item, ModelInfo) else str(item.get("name", mid))
    ctx = item.context_length if isinstance(item, ModelInfo) else item.get("context_length")
    out = item.max_output_tokens if isinstance(item, ModelInfo) else item.get("max_output_tokens")
    caps = item.capabilities if isinstance(item, ModelInfo) else item.get("capabilities", {})
    return {
        "id": make_standard_name(provider, mid),
        "model_id": mid,
        "provider": provider.lower(),
        "name": name,
        "enabled": enabled,
        "context_length": ctx,
        "max_output_tokens": out,
        "capabilities": dict(caps),
    }


def enable_all_models(
    config: Dict[str, Any], provider: str, catalog: List[Any]
) -> Dict[str, Any]:
    """Enables all models in catalog under the given provider."""
    models = config.setdefault("models", [])
    model_map = {m.get("id"): m for m in models if isinstance(m, dict) and "id" in m}
    for item in catalog:
        entry = _model_to_dict(item, provider, enabled=True)
        std_id = entry["id"]
        if std_id in model_map:
            model_map[std_id].update(entry)
        else:
            models.append(entry)
            model_map[std_id] = entry
    return config


def enable_selected_models(
    config: Dict[str, Any], provider: str, catalog: List[Any], selected_ids: List[str]
) -> Dict[str, Any]:
    """Selectively enables chosen model IDs for a provider, disabling others."""
    targets = {s.strip() for s in selected_ids}
    models = config.setdefault("models", [])
    model_map = {m.get("id"): m for m in models if isinstance(m, dict) and "id" in m}
    for item in catalog:
        entry = _model_to_dict(item, provider, enabled=False)
        std_id = entry["id"]
        orig_id = entry["model_id"]
        entry["enabled"] = (std_id in targets or orig_id in targets)
        if std_id in model_map:
            model_map[std_id].update(entry)
        else:
            models.append(entry)
            model_map[std_id] = entry
    return config


def toggle_model(
    config: Dict[str, Any], model_ident: str, provider: Optional[str] = None, enabled: Optional[bool] = None
) -> Dict[str, Any]:
    """Toggles or sets the enabled flag for a specific model."""
    ident = model_ident.strip()
    for m in config.setdefault("models", []):
        if not isinstance(m, dict):
            continue
        matches_id = m.get("id") == ident or m.get("model_id") == ident
        matches_prov = provider is None or m.get("provider") == provider.lower()
        if matches_id and matches_prov:
            m["enabled"] = not m.get("enabled", False) if enabled is None else bool(enabled)
            break
    return config
