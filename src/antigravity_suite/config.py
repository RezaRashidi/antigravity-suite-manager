"""
Centralized Configuration and Path Management for Antigravity Suite.
"""

from __future__ import annotations

from antigravity_suite.config_paths import get_user_home
from antigravity_suite.config_suite import DEFAULT_CONFIG, SuiteConfig

__all__ = [
    "get_user_home",
    "SuiteConfig",
    "DEFAULT_CONFIG",
]
