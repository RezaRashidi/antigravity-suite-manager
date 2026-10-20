"""Data models for Multi-Account subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AccountToken:
    """OAuth tokens and expiration."""

    access_token: str
    refresh_token: str = ""
    expiry: str = ""
    token_type: str = "Bearer"

    def to_dict(self) -> Dict[str, str]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expiry": self.expiry,
            "token_type": self.token_type,
        }


@dataclass
class QuotaBucket:
    """Telemetry for a single quota bucket."""

    family: str  # "gemini" or "claude"
    window: str  # "weekly" or "5h"
    fraction: float = 1.0
    reset_time: str = ""

    def percent(self) -> float:
        return round(self.fraction * 100.0, 1)


@dataclass
class AccountRecord:
    """Full user account state including credentials and telemetry."""

    email: str
    name: str = ""
    sub: str = ""
    token: Optional[AccountToken] = None
    id_token: str = ""
    auth_method: str = "consumer"
    plan: str = "Unknown"
    tier: str = "UNKNOWN_TIER"
    quotas: List[QuotaBucket] = field(default_factory=list)
    is_primary: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "email": self.email,
            "name": self.name,
            "sub": self.sub,
            "token": self.token.to_dict() if self.token else {},
            "id_token": self.id_token,
            "auth_method": self.auth_method,
            "plan": self.plan,
            "tier": self.tier,
            "is_primary": self.is_primary,
            "quotas": [
                {
                    "family": q.family,
                    "window": q.window,
                    "fraction": q.fraction,
                    "reset_time": q.reset_time,
                }
                for q in self.quotas
            ],
        }


@dataclass
class ConversationBinding:
    """Mapping between a conversation cascade and an account."""

    cascade_id: str
    email: str
    model: str = ""
    updated_at: str = ""
