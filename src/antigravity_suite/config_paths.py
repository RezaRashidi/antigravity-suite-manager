"""
User Home and Path Utilities for Antigravity Suite Configuration.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import List


def get_user_home() -> Path:
    """Returns the effective user home directory, respecting REAL_HOME if set."""
    env_home = os.environ.get("REAL_HOME")
    if env_home and os.path.isdir(env_home):
        return Path(env_home).resolve()
    real_user = os.environ.get("REAL_USER") or os.environ.get("SUDO_USER") or os.environ.get("USER")
    if real_user and real_user != "root":
        try:
            import pwd
            return Path(pwd.getpwnam(real_user).pw_dir).resolve()
        except Exception:
            pass
    return Path.home().resolve()


def discover_candidate_ide_dirs(user_home: Path, eff_gemini: Path) -> List[Path]:
    """Finds all candidate IDE and profile configuration directories."""
    p2_env = os.environ.get("ANTIGRAVITY_PROFILE2_DIR")
    p2_path = Path(p2_env).resolve() if p2_env else (user_home / ".antigravity-profile2")
    candidates = [
        user_home / ".gemide",
        user_home / ".gemini-ide",
        eff_gemini,
        p2_path / ".gemini",
    ]
    for p_glob in [
        user_home / ".antigravity-profile-app-*" / ".gemini",
        user_home / ".antigravity-ide-profile-*" / ".gemini",
    ]:
        for match in glob.glob(str(p_glob)):
            candidates.append(Path(match))

    seen, valid = set(), []
    for p in candidates:
        try:
            resolved = p.resolve()
            if resolved.exists() and str(resolved) not in seen:
                seen.add(str(resolved))
                valid.append(resolved)
        except Exception:
            pass
    return valid or [eff_gemini]
