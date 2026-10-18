"""
Suite Configuration Data Structure and Defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from antigravity_suite.config_paths import discover_candidate_ide_dirs, get_user_home


@dataclass(frozen=True)
class SuiteConfig:
    """Immutable suite configuration with configurable overrides."""

    user_home: Path = field(default_factory=get_user_home)
    gemini_dir: Optional[Path] = None
    master_app_dir: Optional[Path] = None
    ide_dirs: List[Path] = field(default_factory=list)
    profile_dirs: List[Path] = field(default_factory=list)

    def __post_init__(self) -> None:
        eff_gemini = (
            self.gemini_dir.resolve()
            if self.gemini_dir is not None and str(self.gemini_dir) not in ("", ".")
            else Path(os.environ.get("ANTIGRAVITY_GEMINI_DIR", self.user_home / ".gemini")).resolve()
        )
        object.__setattr__(self, "gemini_dir", eff_gemini)

        eff_master = (
            self.master_app_dir.resolve()
            if self.master_app_dir is not None and str(self.master_app_dir) not in ("", ".")
            else Path(
                os.environ.get(
                    "ANTIGRAVITY_DATA_DIR",
                    os.environ.get("ANTIGRAVITY_HISTORY_DIR", eff_gemini / "antigravity")
                )
            ).resolve()
        )
        object.__setattr__(self, "master_app_dir", eff_master)

        if not self.ide_dirs:
            object.__setattr__(self, "ide_dirs", discover_candidate_ide_dirs(self.user_home, eff_gemini))

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
        return self.master_app_dir / "conversation_summaries.db"

    @property
    def sub_summaries_db_path(self) -> Path:
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


DEFAULT_CONFIG = SuiteConfig()
