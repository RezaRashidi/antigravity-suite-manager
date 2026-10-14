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
BLUE = '\033[1;38;5;75m'
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

REAL_HOME = os.path.expanduser("~")
CONF_DIR = os.path.join(REAL_HOME, ".config", "antigravity")
PATHS_CONF = os.path.join(CONF_DIR, "paths.conf")

def load_paths_config(detected_app="", detected_ide=""):
    app_dir = detected_app if detected_app else "/opt/antigravity2"
    ide_dir = detected_ide if detected_ide else "/opt/antigravity"
    if os.path.isfile(PATHS_CONF):
        try:
            with open(PATHS_CONF, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == "APP_INSTALL_DIR" and v:
                        app_dir = v
                    elif k == "IDE_INSTALL_DIR" and v:
                        ide_dir = v
        except Exception:
            pass
    return app_dir, ide_dir

def save_paths_config(app_dir, ide_dir):
    os.makedirs(CONF_DIR, exist_ok=True)
    with open(PATHS_CONF, "w", encoding="utf-8") as f:
        f.write("# Antigravity Suite Installation Paths Configuration\n")
        f.write(f'APP_INSTALL_DIR="{app_dir}"\n')
        f.write(f'IDE_INSTALL_DIR="{ide_dir}"\n')

def configure_paths_interactive(installs):
    detected_app = ""
    detected_ide = ""
    for i in installs:
        if ('App' in i['type'] or 'Manager' in i['type']) and not detected_app:
            detected_app = i['path']
        elif 'IDE' in i['type'] and not detected_ide:
            detected_ide = i['path']

    curr_app, curr_ide = load_paths_config(detected_app, detected_ide)
    app_installs = [i for i in installs if 'App' in i['type'] or 'Manager' in i['type']]
    ide_installs = [i for i in installs if 'IDE' in i['type']]

    while True:
        print(f"\n{CYAN}========================================================================================{NC}")
        print(f"{BOLD}{CYAN}                    Configure Antigravity Installation Paths                            {NC}")
        print(f"{CYAN}========================================================================================{NC}")
        print(f"Current Target Paths:")
        print(f"  • Antigravity App: {GREEN}{curr_app}{NC}")
        print(f"  • Antigravity IDE: {GREEN}{curr_ide}{NC}")
        print(f"----------------------------------------------------------------------------------------")
        print(f"{BOLD}Detected System Installations:{NC}")
        if installs:
            for idx, item in enumerate(installs, 1):
                ver = f"v{item['version']}" if item['version'] != "Unknown" else "Unknown"
                tag = ""
                if os.path.realpath(item['path']) == os.path.realpath(curr_app):
                    tag = f" {GREEN}[Active App Target]{NC}"
                elif os.path.realpath(item['path']) == os.path.realpath(curr_ide):
                    tag = f" {GREEN}[Active IDE Target]{NC}"
                print(f"  [{idx}] {item['type']:<20} {ver:<10} in {item['path']}{tag}")
        else:
            print(f"  {YELLOW}None detected outside defaults.{NC}")
        print(f"----------------------------------------------------------------------------------------")
        print("Options:")
        print("  [1] Pick Antigravity App from detected installations")
        print("  [2] Enter custom directory for Antigravity App")
        print("  [3] Pick Antigravity IDE from detected installations")
        print("  [4] Enter custom directory for Antigravity IDE")
        print("  [5] Reset paths to defaults (/opt/antigravity2 & /opt/antigravity)")
        print("  [0] Save and proceed")
        print(f"{CYAN}----------------------------------------------------------------------------------------{NC}")
        try:
            choice = input(f"Select option [0-5, Default: 0]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting path configuration.")
            break

        if choice in ["0", ""]:
            save_paths_config(curr_app, curr_ide)
            print(f"{GREEN}[SUCCESS] Saved installation paths to {PATHS_CONF}{NC}")
            break
        elif choice == "1":
            if not app_installs:
                print(f"{YELLOW}No Antigravity App installations detected on system.{NC}")
                continue
            print("\nSelect detected App installation:")
            for i, it in enumerate(app_installs, 1):
                print(f"  [{i}] {it['path']} ({it['type']} v{it['version']})")
            p_ans = input(f"Choose [1-{len(app_installs)}]: ").strip()
            if p_ans.isdigit() and 1 <= int(p_ans) <= len(app_installs):
                curr_app = app_installs[int(p_ans)-1]['path']
                print(f"{GREEN}[OK] App path updated to: {curr_app}{NC}")
        elif choice == "2":
            new_p = input(f"Enter custom path for Antigravity App [current: {curr_app}]: ").strip()
            if new_p:
                new_p = os.path.expanduser(new_p)
                os.makedirs(new_p, exist_ok=True)
                curr_app = new_p
                print(f"{GREEN}[OK] App path set to: {curr_app}{NC}")
        elif choice == "3":
            if not ide_installs:
                print(f"{YELLOW}No Antigravity IDE installations detected on system.{NC}")
                continue
            print("\nSelect detected IDE installation:")
            for i, it in enumerate(ide_installs, 1):
                print(f"  [{i}] {it['path']} (v{it['version']})")
            p_ans = input(f"Choose [1-{len(ide_installs)}]: ").strip()
            if p_ans.isdigit() and 1 <= int(p_ans) <= len(ide_installs):
                curr_ide = ide_installs[int(p_ans)-1]['path']
                print(f"{GREEN}[OK] IDE path updated to: {curr_ide}{NC}")
        elif choice == "4":
            new_p = input(f"Enter custom path for Antigravity IDE [current: {curr_ide}]: ").strip()
            if new_p:
                new_p = os.path.expanduser(new_p)
                os.makedirs(new_p, exist_ok=True)
                curr_ide = new_p
                print(f"{GREEN}[OK] IDE path set to: {curr_ide}{NC}")
        elif choice == "5":
            curr_app = "/opt/antigravity2"
            curr_ide = "/opt/antigravity"
            print(f"{GREEN}[OK] Reset paths to default: App -> {curr_app}, IDE -> {curr_ide}{NC}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Antigravity System Installation Detector & Path Configurator")
    parser.add_argument('--json', action='store_true', help="Output in JSON format")
    parser.add_argument('--env', action='store_true', help="Output bash export statements")
    parser.add_argument('--configure-paths', action='store_true', help="Interactively configure and select installation paths")
    parser.add_argument('--show-paths', action='store_true', help="Display currently configured installation paths")
    parser.add_argument('--set-app-dir', type=str, help="Set custom Antigravity App installation directory")
    parser.add_argument('--set-ide-dir', type=str, help="Set custom Antigravity IDE installation directory")
    parser.add_argument('--set-defaults-if-missing', action='store_true', help="Create default paths.conf if not existing")
    args = parser.parse_args()

    installs = scan_installations()

    if args.set_app_dir or args.set_ide_dir:
        curr_app, curr_ide = load_paths_config()
        if args.set_app_dir:
            curr_app = os.path.expanduser(args.set_app_dir)
            os.makedirs(curr_app, exist_ok=True)
        if args.set_ide_dir:
            curr_ide = os.path.expanduser(args.set_ide_dir)
            os.makedirs(curr_ide, exist_ok=True)
        save_paths_config(curr_app, curr_ide)
        print(f"{GREEN}[SUCCESS] Saved installation paths to {PATHS_CONF}:{NC}")
        print(f"  • App: {curr_app}")
        print(f"  • IDE: {curr_ide}")
    elif args.set_defaults_if_missing:
        if not os.path.isfile(PATHS_CONF):
            det_app = ""
            det_ide = ""
            for i in installs:
                if ('App' in i['type'] or 'Manager' in i['type']) and not det_app:
                    det_app = i['path']
                elif 'IDE' in i['type'] and not det_ide:
                    det_ide = i['path']
            app_p, ide_p = load_paths_config(det_app, det_ide)
            save_paths_config(app_p, ide_p)
    elif args.configure_paths:
        configure_paths_interactive(installs)
    elif args.show_paths:
        app_p, ide_p = load_paths_config()
        print(f"Antigravity App: {app_p}")
        print(f"Antigravity IDE: {ide_p}")
    elif args.json:
        print(json.dumps(installs, indent=2))
    elif args.env:
        app_path = ""
        app_ver = ""
        ide_path = ""
        ide_ver = ""
        # Check paths.conf first
        conf_app, conf_ide = load_paths_config()
        for i in installs:
            if not app_path and ('App' in i['type'] or 'Manager' in i['type']):
                app_path = i['path']
                app_ver = i['version']
            elif not ide_path and 'IDE' in i['type']:
                ide_path = i['path']
                ide_ver = i['version']
        final_app = conf_app if conf_app else (app_path or "/opt/antigravity2")
        final_ide = conf_ide if conf_ide else (ide_path or "/opt/antigravity")
        print(f'ANTIGRAVITY_DETECTED_APP="{final_app}"')
        print(f'ANTIGRAVITY_DETECTED_APP_VER="{app_ver}"')
        print(f'ANTIGRAVITY_DETECTED_IDE="{final_ide}"')
        print(f'ANTIGRAVITY_DETECTED_IDE_VER="{ide_ver}"')
    else:
        print_table(installs)
