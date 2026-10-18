"""
Launcher script inspection and executable path rewriting.
"""

from __future__ import annotations

import os
import re

from antigravity_suite.detect.launcher_writer import create_launcher_and_desktop, toggle_keyring_for_path


def get_launcher_binary(launcher_path: str) -> str:
    if not os.path.isfile(launcher_path):
        return ""
    try:
        with open(launcher_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("exec "):
                    m = re.search(r'exec\s+("[^"]+"|\'[^\']+\'|\S+)', line.strip())
                    if m:
                        return m.group(1).strip('"').strip("'")
    except Exception:
        pass
    return ""


def update_launcher_binary(launcher_path: str, new_binary: str) -> bool:
    if not os.path.isfile(launcher_path):
        return False
    try:
        with open(launcher_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r'exec\s+("[^"]+"|\'[^\']+\'|\S+)', f'exec "{new_binary}"', content, count=1)
        with open(launcher_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception:
        return False


def update_launcher_profile_path(launcher_f: str, is_acc2: bool, old_p: str, new_p: str) -> None:
    if not os.path.isfile(launcher_f):
        return
    with open(launcher_f, "r", encoding="utf-8") as f:
        l_content = f.read()
    if is_acc2:
        l_content = re.sub(r'export PROFILE2="[^"]+"', f'export PROFILE2="{new_p}"', l_content)
        l_content = re.sub(r'export PROFILE="[^"]+"', f'export PROFILE2="{new_p}"', l_content)
    else:
        l_content = re.sub(r'export PROFILE="[^"]+"', f'export PROFILE="{new_p}"', l_content)

    old_p_clean = old_p.rstrip("/")
    new_p_clean = new_p.rstrip("/")
    if old_p_clean in l_content:
        l_content = l_content.replace(old_p_clean, new_p_clean)
    if old_p in l_content:
        l_content = l_content.replace(old_p, new_p)

    old_base = os.path.basename(old_p_clean)
    new_base = os.path.basename(new_p_clean)
    if old_base and new_base and old_base != new_base:
        suffix = re.escape(new_base[len(old_base):]) if new_base.startswith(old_base) else ""
        prefix = re.escape(new_base[:len(new_base) - len(old_base)]) if new_base.endswith(old_base) else ""
        pat = rf"{re.escape(old_base)}"
        if suffix:
            pat = rf"{pat}(?!{suffix})"
        if prefix:
            pat = rf"(?<!{prefix}){pat}"
        l_content = re.sub(pat, new_base, l_content)

    with open(launcher_f, "w", encoding="utf-8") as f:
        f.write(l_content)


__all__ = [
    "get_launcher_binary",
    "update_launcher_binary",
    "update_launcher_profile_path",
    "create_launcher_and_desktop",
    "toggle_keyring_for_path",
]
