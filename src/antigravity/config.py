"""
Centralized Configuration and Path Management for Antigravity Suite.

Provides generalized path resolution, environment variable overrides,
and runtime constants without hardcoded user directories.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


def get_user_home() -> Path:
    """Returns the effective user home directory, respecting REAL_HOME if set."""
    env_home = os.environ.get("REAL_HOME")
    if env_home and os.path.isdir(env_home):
        return Path(env_home).resolve()
    return Path.home().resolve()


@dataclass(frozen=True)
class SuiteConfig:
    """Immutable suite configuration with configurable overrides."""

    user_home: Path = field(default_factory=get_user_home)
    gemini_dir: Path = field(default=Path())
    master_app_dir: Path = field(default=Path())
    ide_dirs: List[Path] = field(default_factory=list)
    profile_dirs: List[Path] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gemini_dir",
            self.gemini_dir
            if self.gemini_dir != Path()
            else Path(os.environ.get("ANTIGRAVITY_GEMINI_DIR", self.user_home / ".gemini")).resolve(),
        )
        object.__setattr__(
            self,
            "master_app_dir",
            self.master_app_dir
            if self.master_app_dir != Path()
            else Path(os.environ.get("ANTIGRAVITY_APP_DIR", self.gemini_dir / "antigravity")).resolve(),
        )
        if not self.ide_dirs:
            candidate_ides = [
                self.user_home / ".gemide",
                self.user_home / ".gemini-ide",
                self.gemini_dir,
            ]
            valid_ides = [p.resolve() for p in candidate_ides if p.exists() or p == candidate_ides[0]]
            object.__setattr__(self, "ide_dirs", valid_ides)

    @property
    def conversations_dir(self) -> Path:
        return self.master_app_dir / "conversations"

    @property
    def brain_dir(self) -> Path:
        return self.master_app_dir / "brain"

    @property
    def annotations_dir(self) -> Path:
        return self.master_app_dir / "annotations"

    @property
    def summaries_db_path(self) -> Path:
        return self.conversations_dir / "conversation_summaries.db"

    @property
    def summaries_proto_path(self) -> Path:
        return self.master_app_dir / "agyhub_summaries_proto.pb"

    @property
    def default_workspace_uri(self) -> str:
        return f"file://{self.user_home}"

    @property
    def default_project_id(self) -> str:
        return "outside-of-project"


# Global default configuration instance
DEFAULT_CONFIG = SuiteConfig()
