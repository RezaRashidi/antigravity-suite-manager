#!/usr/bin/env python3
"""
Antigravity Installation Detector
Scans Linux filesystem, PATH, desktop entries, and active processes
to identify installed Google Antigravity App and Antigravity IDE instances.
"""

import os
import sys
import glob
import json
import struct
import re
import argparse

GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[1;34m'
CYAN = '\033[1;36m'
RED = '\033[1;31m'
NC = '\033[0m'
BOLD = '\033[1m'

def inspect_app_dir(d):
    asar = os.path.join(d, 'resources', 'app.asar')
    if not os.path.isfile(asar):
        return None
    ver = "Unknown"
    try:
        with open(asar, 'rb') as f:
            magic, h_s, h_o, j_len = struct.unpack('<IIII', f.read(16))
            hdr = json.loads(f.read(j_len).decode('utf-8'))
            curr = hdr.get('files', {}).get('package.json', {})
            if 'offset' in curr and 'size' in curr:
                f.seek(16 + j_len + int(curr['offset']))
                raw = f.read(min(curr['size'] + 50, 1024)).decode('utf-8', errors='ignore')
                m = re.search(r'"version"\s*:\s*"([^"]+)"', raw)
                if m:
                    ver = m.group(1)
    except Exception:
        pass

    exe = None
    for name in ['antigravity', 'antigravity-app', 'antigravity-manager']:
        p = os.path.join(d, name)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            exe = p
            break

    label = 'Antigravity Manager' if (exe and 'manager' in exe) or 'manager' in d else 'Antigravity App'
    res_dir = os.path.join(d, 'resources')
    writable = os.access(d, os.W_OK) and (not os.path.isdir(res_dir) or os.access(res_dir, os.W_OK))

    return {
        'type': label,
        'version': ver,
        'path': d,
        'executable': exe,
        'writable': writable
    }

def inspect_ide_dir(d):
    prod = os.path.join(d, 'resources', 'app', 'product.json')
    pkg = os.path.join(d, 'resources', 'app', 'package.json')
    if not (os.path.isfile(prod) or os.path.isfile(pkg)):
        return None
    ver = "Unknown"
    try:
        if os.path.isfile(prod):
            with open(prod, 'r', encoding='utf-8') as f:
                data = json.load(f)
                ver = data.get('ideVersion') or data.get('version') or ver
        if ver == "Unknown" and os.path.isfile(pkg):
            with open(pkg, 'r', encoding='utf-8') as f:
                data = json.load(f)
                ver = data.get('version') or ver
    except Exception:
        pass

    exe = None
    for rel in ['antigravity-ide', 'bin/antigravity-ide', 'code']:
        p = os.path.join(d, rel)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            exe = p
            break

    res_dir = os.path.join(d, 'resources')
    writable = os.access(d, os.W_OK) and (not os.path.isdir(res_dir) or os.access(res_dir, os.W_OK))

    return {
        'type': 'Antigravity IDE',
        'version': ver,
        'path': d,
        'executable': exe,
        'writable': writable
    }

def get_running_paths():
    paths = set()
    try:
        for pid_dir in glob.glob('/proc/[0-9]*'):
            try:
                exe = os.path.realpath(os.path.join(pid_dir, 'exe'))
                if 'antigravity' in exe.lower():
                    paths.add(exe)
            except Exception:
                continue
    except Exception:
        pass
    return paths

def scan_installations():
    candidates = set()
    roots = [
        '/opt',
        '/usr/share',
        '/usr/lib',
        '/usr/local/share',
        os.path.expanduser('~/.local/share'),
        os.path.expanduser('~/.local/lib'),
        os.path.expanduser('~/opt'),
        os.path.expanduser('~/.antigravity')
    ]

    for r in roots:
        if os.path.isdir(r):
            for pat in ['*antigravity*', '*Antigravity*']:
                for m in glob.glob(os.path.join(r, pat)):
                    if os.path.isdir(m):
                        candidates.add(os.path.realpath(m))

    # Check PATH binaries
    for p in os.environ.get('PATH', '').split(':'):
        for cmd in ['antigravity', 'antigravity-ide', 'antigravity-1', 'antigravity-acc2', 'antigravity-manager']:
            fp = os.path.join(p, cmd)
            if os.path.isfile(fp):
                rp = os.path.realpath(fp)
                d = os.path.dirname(rp)
                candidates.add(d)
                if os.path.basename(d) in ['bin', 'MacOS']:
                    candidates.add(os.path.dirname(d))

    # Check .desktop files
    for ddir in [os.path.expanduser('~/.local/share/applications'), '/usr/share/applications']:
        if os.path.isdir(ddir):
            for df in glob.glob(os.path.join(ddir, '*antigravity*.desktop')) + glob.glob(os.path.join(ddir, '*Antigravity*.desktop')):
                try:
                    with open(df, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            if line.startswith('Exec='):
                                cmd = line.split('=', 1)[1].strip().split()[0]
                                if os.path.isfile(cmd):
                                    rp = os.path.realpath(cmd)
                                    d = os.path.dirname(rp)
                                    candidates.add(d)
                                    if os.path.basename(d) == 'bin':
                                        candidates.add(os.path.dirname(d))
                except Exception:
                    pass

    # Check running processes
    for rp in get_running_paths():
        d = os.path.dirname(rp)
        candidates.add(d)
        if os.path.basename(d) == 'bin':
            candidates.add(os.path.dirname(d))

    installations = []
    seen_paths = set()

    for c in sorted(candidates):
        real_c = os.path.realpath(c)
        if real_c in seen_paths:
            continue
        ide = inspect_ide_dir(real_c)
        if ide:
            installations.append(ide)
            seen_paths.add(real_c)
            continue
        app = inspect_app_dir(real_c)
        if app:
            installations.append(app)
            seen_paths.add(real_c)
            continue

    return installations

def print_table(installs):
    print(f"{CYAN}========================================================================================{NC}")
    print(f"{BOLD}{CYAN}                    Detected Antigravity Installations on System                       {NC}")
    print(f"{CYAN}========================================================================================{NC}")
    if not installs:
        print(f"{RED}No Antigravity installations found on this system.{NC}")
        print(f"{YELLOW}Run 'manage-antigravity.sh install' to install Antigravity App and IDE.{NC}")
        print(f"{CYAN}========================================================================================{NC}")
        return

    print(f"{BOLD}{BLUE}Type                 Version     Writable    Executable                  Path{NC}")
    print(f"----------------------------------------------------------------------------------------")
    for item in installs:
        t = item['type']
        v = f"v{item['version']}" if item['version'] != "Unknown" else "Unknown"
        w = f"{GREEN}Yes{NC}" if item['writable'] else f"{RED}No (Root){NC}"
        exe_base = os.path.basename(item['executable']) if item['executable'] else f"{RED}None{NC}"
        p = item['path']
        print(f"{t:<20} {v:<11} {w:<20} {exe_base:<27} {p}")
    print(f"{CYAN}========================================================================================{NC}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Antigravity System Installation Detector")
    parser.add_argument('--json', action='store_true', help="Output in JSON format")
    parser.add_argument('--env', action='store_true', help="Output bash export statements")
    args = parser.parse_args()

    installs = scan_installations()

    if args.json:
        print(json.dumps(installs, indent=2))
    elif args.env:
        app_path = ""
        app_ver = ""
        ide_path = ""
        ide_ver = ""
        for i in installs:
            if i['type'] == 'Antigravity App' and not app_path:
                app_path = i['path']
                app_ver = i['version']
            elif i['type'] == 'Antigravity IDE' and not ide_path:
                ide_path = i['path']
                ide_ver = i['version']
        print(f'ANTIGRAVITY_DETECTED_APP="{app_path}"')
        print(f'ANTIGRAVITY_DETECTED_APP_VER="{app_ver}"')
        print(f'ANTIGRAVITY_DETECTED_IDE="{ide_path}"')
        print(f'ANTIGRAVITY_DETECTED_IDE_VER="{ide_ver}"')
    else:
        print_table(installs)
