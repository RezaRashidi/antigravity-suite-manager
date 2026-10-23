"""
Status inspection helpers for Antigravity installations and patches.
"""

from __future__ import annotations

import glob
import json
import os
import re
import struct
from typing import Any, List, Optional, Tuple

G, Y, R, B, C, NC, BOLD = '\033[1;32m', '\033[1;33m', '\033[1;31m', '\033[1;38;5;75m', '\033[1;36m', '\033[0m', '\033[1m'


def get_app_version(app_dir: str) -> Optional[str]:
    asar_path = os.path.join(app_dir, 'resources', 'app.asar')
    if not os.path.isfile(asar_path): return None
    try:
        with open(asar_path, 'rb') as f:
            magic, header_size, header_obj_size, json_len = struct.unpack('<IIII', f.read(16))
            header = json.loads(f.read(json_len).decode('utf-8'))
            curr = header.get('files', {}).get('package.json', {})
            if 'offset' in curr and 'size' in curr:
                f.seek(8 + header_size + int(curr['offset']))
                pkg_raw = f.read(int(curr['size'])).decode('utf-8', errors='ignore')
                try:
                    pkg_data = json.loads(pkg_raw)
                    if 'version' in pkg_data: return str(pkg_data['version'])
                except Exception:
                    m = re.search(r'"version"\s*:\s*"([^"]+)"', pkg_raw)
                    if m: return m.group(1)
    except Exception: pass
    return 'Unknown'


def get_ide_version(ide_dir: str) -> Optional[str]:
    prod_path = os.path.join(ide_dir, 'resources', 'app', 'product.json')
    if not os.path.isfile(prod_path): return None
    try:
        with open(prod_path, 'r', encoding='utf-8') as f:
            prod = json.load(f)
            return prod.get('ideVersion') or prod.get('version') or 'Unknown'
    except Exception: pass
    return 'Unknown'


def check_app_rtl(app_dir: str) -> str:
    return _check_asar_content(app_dir, b'/* ANTIGRAVITY RTL PATCH */')


def check_app_f5(app_dir: str) -> str:
    return _check_asar_content(app_dir, b'restartLanguageServer')


def check_app_open_ide(app_dir: str) -> str:
    return _check_asar_content(app_dir, b'ANTIGRAVITY_SUITE_OPEN_IDE_PATCH')


def _check_asar_content(app_dir: str, needle: bytes) -> str:
    asar_path = os.path.join(app_dir, 'resources', 'app.asar')
    if not os.path.isfile(asar_path): return f"{R}Missing{NC}"
    try:
        with open(asar_path, 'rb') as f:
            while True:
                chunk = f.read(10 * 1024 * 1024)
                if not chunk: break
                if needle in chunk: return f"{G}Applied{NC}"
    except Exception: pass
    return f"{Y}Not Applied{NC}"


def check_ide_rtl(ide_dir: str) -> str:
    main_js = os.path.join(ide_dir, 'resources', 'app', 'out', 'main.js')
    if not os.path.isfile(main_js): return f"{R}Missing{NC}"
    try:
        with open(main_js, 'r', encoding='utf-8') as f:
            txt = f.read(1024)
            if 'antigravity-rtl-main.js' in txt or os.path.isfile(main_js + '.rtl-bak'): return f"{G}Applied{NC}"
    except Exception: pass
    return f"{Y}Not Applied{NC}"
