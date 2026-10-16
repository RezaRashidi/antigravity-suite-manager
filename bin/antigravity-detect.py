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
import subprocess
import shutil
import datetime
import shlex

GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[1;38;5;75m'
CYAN = '\033[1;36m'
RED = '\033[1;31m'
NC = '\033[0m'
BOLD = '\033[1m'

REAL_USER = os.environ.get("REAL_USER")
if not REAL_USER:
    REAL_USER = os.environ.get("SUDO_USER") or os.environ.get("USER") or os.environ.get("LOGNAME")
REAL_HOME = os.environ.get("REAL_HOME")
if not REAL_HOME:
    if REAL_USER and REAL_USER != "root":
        try:
            import pwd
            REAL_HOME = pwd.getpwnam(REAL_USER).pw_dir
        except Exception:
            REAL_HOME = os.path.expanduser("~")
    else:
        REAL_HOME = os.path.expanduser("~")

CONF_DIR = os.path.join(REAL_HOME, ".config", "antigravity")
PATHS_CONF = os.path.join(CONF_DIR, "paths.conf")

def is_acc1_running(real_home=None):
    home = real_home or REAL_HOME
    target_udd = os.path.realpath(f"{home}/.config/Antigravity")
    try:
        pids = subprocess.run(["pgrep", "-f", "Antigravity"], capture_output=True, text=True).stdout.strip().split()
        for pid in pids:
            try:
                with open(f"/proc/{pid}/cmdline", "r", errors="ignore") as f:
                    cmd_parts = [p for p in f.read().split('\x00') if p]
                    if not cmd_parts:
                        continue
                    udd = None
                    for part in cmd_parts:
                        if part.startswith("--user-data-dir="):
                            udd = part.split("=", 1)[1]
                            break
                    if udd:
                        if os.path.realpath(os.path.expanduser(udd)) == target_udd:
                            return True
                    else:
                        cmd_line = " ".join(cmd_parts)
                        if "antigravity-profile" not in cmd_line and "Antigravity" in cmd_line:
                            if not any(arg.startswith("--user-data-dir=") for arg in cmd_parts):
                                return True
            except Exception:
                continue
    except Exception:
        pass
    return False

def is_main_ide_running(real_home=None):
    home = real_home or REAL_HOME
    target_udd = os.path.realpath(f"{home}/.antigravity-ide")
    try:
        pids = subprocess.run(["pgrep", "-f", "antigravity-ide"], capture_output=True, text=True).stdout.strip().split()
        for pid in pids:
            try:
                with open(f"/proc/{pid}/cmdline", "r", errors="ignore") as f:
                    cmd_parts = [p for p in f.read().split('\x00') if p]
                    if not cmd_parts:
                        continue
                    cmd_line = " ".join(cmd_parts)
                    if ".antigravity-ide-profile-" in cmd_line or "antigravity-ide-profile" in cmd_line:
                        continue
                    udd = None
                    for part in cmd_parts:
                        if part.startswith("--user-data-dir="):
                            udd = part.split("=", 1)[1]
                            break
                    if udd:
                        if os.path.realpath(os.path.expanduser(udd)) == target_udd:
                            return True
                    else:
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False

def update_launcher_profile_path(launcher_f, is_acc2, old_p, new_p):
    if not os.path.isfile(launcher_f):
        return
    with open(launcher_f, "r", encoding="utf-8") as f:
        l_content = f.read()
    if is_acc2:
        l_content = re.sub(r'export PROFILE2="[^"]+"', f'export PROFILE2="{new_p}"', l_content)
        l_content = re.sub(r'export PROFILE="[^"]+"', f'export PROFILE2="{new_p}"', l_content)
    else:
        l_content = re.sub(r'export PROFILE="[^"]+"', f'export PROFILE="{new_p}"', l_content)

    old_p_clean = old_p.rstrip('/')
    new_p_clean = new_p.rstrip('/')
    if old_p_clean in l_content:
        l_content = l_content.replace(old_p_clean, new_p_clean)
    if old_p in l_content:
        l_content = l_content.replace(old_p, new_p)

    old_base = os.path.basename(old_p_clean)
    new_base = os.path.basename(new_p_clean)
    if old_base and new_base and old_base != new_base:
        suffix = re.escape(new_base[len(old_base):]) if new_base.startswith(old_base) else ''
        prefix = re.escape(new_base[:len(new_base)-len(old_base)]) if new_base.endswith(old_base) else ''
        pat = rf'{re.escape(old_base)}'
        if suffix:
            pat = rf'{pat}(?!{suffix})'
        if prefix:
            pat = rf'(?<!{prefix}){pat}'
        l_content = re.sub(pat, new_base, l_content)

    with open(launcher_f, "w", encoding="utf-8") as f:
        f.write(l_content)


def inspect_app_dir(d):
    # Strictly exclude unofficial third-party apps like Antigravity Manager
    if 'manager' in d.lower():
        return None
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
                f.seek(8 + h_s + int(curr['offset']))
                pkg_raw = f.read(int(curr['size'])).decode('utf-8', errors='ignore')
                try:
                    pkg_data = json.loads(pkg_raw)
                    if 'version' in pkg_data:
                        ver = str(pkg_data['version'])
                except Exception:
                    m = re.search(r'"version"\s*:\s*"([^"]+)"', pkg_raw)
                    if m:
                        ver = m.group(1)
    except Exception:
        pass

    exe = None
    for name in ['antigravity', 'antigravity-app']:
        p = os.path.join(d, name)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            exe = p
            break

    if not exe:
        for f in os.listdir(d):
            if f.startswith('antigravity') and 'manager' not in f and os.access(os.path.join(d, f), os.X_OK):
                exe = os.path.join(d, f)
                break

    if not exe or 'manager' in exe.lower():
        return None

    res_dir = os.path.join(d, 'resources')
    writable = os.access(d, os.W_OK) and (not os.path.isdir(res_dir) or os.access(res_dir, os.W_OK))

    return {
        'type': 'Antigravity App',
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

    # Check configured paths in paths.conf
    if os.path.isfile(PATHS_CONF):
        try:
            with open(PATHS_CONF, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        k, v = line.split('=', 1)
                        v = v.strip().strip('"').strip("'")
                        if v:
                            if k in ['CUSTOM_PATHS', 'CUSTOM_ANTIGRAVITY_PATHS']:
                                for cp in v.split(':'):
                                    if cp.strip() and os.path.isdir(os.path.expanduser(cp.strip())):
                                        candidates.add(os.path.realpath(os.path.expanduser(cp.strip())))
                            elif k in ['APP_INSTALL_DIR', 'IDE_INSTALL_DIR']:
                                if os.path.isdir(os.path.expanduser(v)):
                                    candidates.add(os.path.realpath(os.path.expanduser(v)))
        except Exception:
            pass

    # Check PATH binaries
    for p in os.environ.get('PATH', '').split(':'):
        for cmd in ['antigravity', 'antigravity-ide', 'antigravity-1', 'antigravity-acc2']:
            fp = os.path.join(p, cmd)
            if os.path.isfile(fp):
                rp = os.path.realpath(fp)
                d = os.path.dirname(rp)
                if 'manager' not in d.lower():
                    candidates.add(d)
                if os.path.basename(d) in ['bin', 'MacOS']:
                    candidates.add(os.path.dirname(d))

    # Check .desktop files
    for ddir in [os.path.expanduser('~/.local/share/applications'), '/usr/share/applications']:
        if os.path.isdir(ddir):
            for df in glob.glob(os.path.join(ddir, '*antigravity*.desktop')) + glob.glob(os.path.join(ddir, '*Antigravity*.desktop')):
                if 'manager' in df.lower():
                    continue
                try:
                    with open(df, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            if line.startswith('Exec='):
                                tokens = shlex.split(line.split('=', 1)[1].strip())
                                cmd = tokens[0] if tokens else ""
                                if os.path.isfile(cmd):
                                    rp = os.path.realpath(cmd)
                                    d = os.path.dirname(rp)
                                    if 'manager' not in d.lower():
                                        candidates.add(d)
                                    if os.path.basename(d) == 'bin':
                                        candidates.add(os.path.dirname(d))
                except Exception:
                    pass

    # Check running processes
    for rp in get_running_paths():
        if 'manager' in rp.lower():
            continue
        d = os.path.dirname(rp)
        candidates.add(d)
        if os.path.basename(d) == 'bin':
            candidates.add(os.path.dirname(d))

    installations = []
    seen_paths = set()

    for c in sorted(candidates):
        real_c = os.path.realpath(c)
        if real_c in seen_paths or 'manager' in real_c.lower():
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

REAL_HOME = os.environ.get("REAL_HOME", "")
if not REAL_HOME:
    try:
        import pwd
        user = os.environ.get("SUDO_USER") or os.environ.get("USER") or pwd.getpwuid(os.getuid()).pw_name
        REAL_HOME = pwd.getpwnam(user).pw_dir
    except Exception:
        REAL_HOME = os.path.expanduser("~")
CONF_DIR = os.path.join(REAL_HOME, ".config", "antigravity")
PATHS_CONF = os.path.join(CONF_DIR, "paths.conf")

def get_launcher_binary(launcher_path):
    if not os.path.isfile(launcher_path):
        return ""
    try:
        with open(launcher_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('exec '):
                    m = re.search(r'exec\s+("[^"]+"|\'[^\']+\'|\S+)', line)
                    if m:
                        return m.group(1).strip('"').strip("'")
    except Exception:
        pass
    return ""

def update_launcher_binary(launcher_path, new_binary):
    if not os.path.isfile(launcher_path):
        return False
    try:
        with open(launcher_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = re.sub(r'exec\s+("[^"]+"|\'[^\']+\'|\S+)', f'exec "{new_binary}"', content, count=1)
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception:
        return False

def scan_clones(curr_app="", curr_ide=""):
    clones = []
    local_bin = os.path.join(REAL_HOME, '.local', 'bin')
    local_apps = os.path.join(REAL_HOME, '.local', 'share', 'applications')

    has_other_app_accounts = False
    acc2_profile = os.path.join(REAL_HOME, '.antigravity-profile2')
    if os.path.isdir(acc2_profile) or os.path.isfile(os.path.join(local_bin, 'antigravity-acc2')):
        has_other_app_accounts = True
    else:
        for p in glob.glob(os.path.join(REAL_HOME, '.antigravity-profile-app-*')):
            if '.bak' not in p and '.removed' not in p and os.path.isdir(p):
                has_other_app_accounts = True
                break

    # 1. Primary App (Account 1 - Default / Single Account)
    acc1_profile = os.path.join(REAL_HOME, '.gemini')
    acc1_launcher = os.path.join(local_bin, 'antigravity') if not has_other_app_accounts else os.path.join(local_bin, 'antigravity-1')
    if not os.path.isfile(acc1_launcher):
        if os.path.isfile(os.path.join(local_bin, 'antigravity')):
            acc1_launcher = os.path.join(local_bin, 'antigravity')
        elif os.path.isfile(os.path.join(local_bin, 'antigravity-1')):
            acc1_launcher = os.path.join(local_bin, 'antigravity-1')

    acc1_desktop = os.path.join(local_apps, 'antigravity.desktop') if not has_other_app_accounts else os.path.join(local_apps, 'antigravity-1.desktop')
    if not os.path.isfile(acc1_desktop):
        if os.path.isfile(os.path.join(local_apps, 'antigravity.desktop')):
            acc1_desktop = os.path.join(local_apps, 'antigravity.desktop')
        elif os.path.isfile(os.path.join(local_apps, 'antigravity-1.desktop')):
            acc1_desktop = os.path.join(local_apps, 'antigravity-1.desktop')

    acc1_running = is_acc1_running(REAL_HOME)
    acc1_cache = os.path.join(acc1_profile, 'cache', 'antigravity-keyring-unavailable')

    app1_name = 'Antigravity' if not has_other_app_accounts else 'Antigravity (Account 1 - Default)'
    app1_role = 'Primary Application' if not has_other_app_accounts else 'Primary Account'
    app1_wm = 'antigravity' if not has_other_app_accounts else 'antigravity-1'

    # Only register app1 if launcher exists, desktop exists, or the engine directory actually exists
    if os.path.isfile(acc1_launcher) or os.path.isfile(acc1_desktop) or (curr_app and os.path.isdir(curr_app)):
        clones.append({
            'id': 'app1',
            'name': app1_name,
            'type': 'App',
            'role': app1_role,
            'profile_dir': acc1_profile,
            'launcher': acc1_launcher if os.path.isfile(acc1_launcher) else (curr_app if os.path.isdir(curr_app) else 'Default binary'),
            'desktop': acc1_desktop,
            'wm_class': app1_wm,
            'history_mode': 'Master Shared Pool',
            'keyring_mode': 'Normal (File Storage)' if os.path.isfile(acc1_cache) else 'GNOME Keyring',
            'status': 'Running' if acc1_running else 'Stopped'
        })

    # 2. Account 2 (Cloned)
    acc2_profile = os.path.join(REAL_HOME, '.antigravity-profile2')
    if os.path.isdir(acc2_profile) or os.path.isfile(os.path.join(local_bin, 'antigravity-acc2')):
        acc2_running = subprocess.run(['pgrep', '-f', 'antigravity-profile2.*Antigravity'], capture_output=True).returncode == 0
        acc2_shared = os.path.islink(os.path.join(acc2_profile, '.gemini', 'antigravity'))
        acc2_cache = os.path.join(acc2_profile, '.gemini', 'cache', 'antigravity-keyring-unavailable')
        clones.append({
            'id': 'app2',
            'name': 'Antigravity (Account 2)',
            'type': 'App Clone',
            'role': 'Secondary Account',
            'profile_dir': acc2_profile,
            'launcher': os.path.join(local_bin, 'antigravity-acc2'),
            'desktop': os.path.join(local_apps, 'antigravity-2.desktop'),
            'wm_class': 'antigravity-2',
            'history_mode': 'Shared 3-Way Sync' if acc2_shared else 'Isolated Private',
            'keyring_mode': 'Normal (File Storage)' if os.path.isfile(acc2_cache) else 'GNOME Keyring',
            'status': 'Running' if acc2_running else 'Stopped'
        })

    # 3. Custom App Clones (~/.antigravity-profile-app-*)
    for p in sorted(glob.glob(os.path.join(REAL_HOME, '.antigravity-profile-app-*'))):
        if '.bak' in p or '.removed' in p:
            continue
        cname = os.path.basename(p).replace('.antigravity-profile-app-', '')
        c_running = subprocess.run(['pgrep', '-f', f'{os.path.basename(p)}.*Antigravity'], capture_output=True).returncode == 0
        c_shared = os.path.islink(os.path.join(p, '.gemini', 'antigravity'))
        c_cache = os.path.join(p, '.gemini', 'cache', 'antigravity-keyring-unavailable')
        clones.append({
            'id': f'app-{cname}',
            'name': f'Antigravity (App: {cname})',
            'type': 'App Clone',
            'role': f'Custom Account ({cname})',
            'profile_dir': p,
            'launcher': os.path.join(local_bin, f'antigravity-app-{cname}'),
            'desktop': os.path.join(local_apps, f'antigravity-app-{cname}.desktop'),
            'wm_class': f'antigravity-app-{cname}',
            'history_mode': 'Shared 3-Way Sync' if c_shared else 'Isolated Private',
            'keyring_mode': 'Normal (File Storage)' if os.path.isfile(c_cache) else 'GNOME Keyring',
            'status': 'Running' if c_running else 'Stopped'
        })

    # 4. Primary IDE
    ide_profile = os.path.join(REAL_HOME, '.gemini', 'antigravity-ide')
    ide_launcher = os.path.join(local_bin, 'antigravity-ide')
    ide_desktop = os.path.join(local_apps, 'antigravity-ide.desktop')
    ide_running = is_main_ide_running(REAL_HOME)
    ide_shared = os.path.islink(os.path.join(ide_profile, 'conversations'))
    ide_cache = os.path.join(REAL_HOME, '.gemide', 'cache', 'antigravity-keyring-unavailable')
    if not os.path.isfile(ide_cache):
        ide_cache = os.path.join(REAL_HOME, '.gemini', 'antigravity-ide', 'cache', 'antigravity-keyring-unavailable')
    # Only register ide1 if launcher exists, desktop exists, or the engine directory actually exists
    if os.path.isfile(ide_launcher) or os.path.isfile(ide_desktop) or (curr_ide and os.path.isdir(curr_ide)):
        clones.append({
            'id': 'ide1',
            'name': 'Antigravity IDE (Primary)',
            'type': 'IDE',
            'role': 'Primary IDE',
            'profile_dir': ide_profile,
            'launcher': ide_launcher if os.path.isfile(ide_launcher) else (curr_ide if os.path.isdir(curr_ide) else 'Default binary'),
            'desktop': ide_desktop,
            'wm_class': 'antigravity-ide',
            'history_mode': 'Shared 3-Way Sync' if ide_shared else 'Isolated Private',
            'keyring_mode': 'Normal (File Storage)' if os.path.isfile(ide_cache) else 'GNOME Keyring',
            'status': 'Running' if ide_running else 'Stopped'
        })

    # 5. Custom IDE Clones (~/.antigravity-ide-profile-*)
    for p in sorted(glob.glob(os.path.join(REAL_HOME, '.antigravity-ide-profile-*'))):
        if '.bak' in p or '.removed' in p:
            continue
        cname = os.path.basename(p).replace('.antigravity-ide-profile-', '')
        c_running = subprocess.run(['pgrep', '-f', f'{os.path.basename(p)}'], capture_output=True).returncode == 0
        c_shared = os.path.islink(os.path.join(p, '.gemini', 'antigravity-ide', 'conversations')) or \
                   os.path.islink(os.path.join(p, '.gemini', 'antigravity-ide'))
        c_cache = os.path.join(p, '.gemini', 'cache', 'antigravity-keyring-unavailable')
        clones.append({
            'id': f'ide-{cname}',
            'name': f'Antigravity IDE ({cname})',
            'type': 'IDE Clone',
            'role': f'Custom IDE ({cname})',
            'profile_dir': p,
            'launcher': os.path.join(local_bin, f'antigravity-ide-{cname}'),
            'desktop': os.path.join(local_apps, f'antigravity-ide-{cname}.desktop'),
            'wm_class': f'antigravity-ide-{cname}',
            'history_mode': 'Shared 3-Way Sync' if c_shared else 'Isolated Private',
            'keyring_mode': 'Normal (File Storage)' if os.path.isfile(c_cache) else 'GNOME Keyring',
            'status': 'Running' if c_running else 'Stopped'
        })

    return clones

def load_paths_config(detected_app="", detected_ide=""):
    app_dir = ""
    ide_dir = ""
    custom_paths = []
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
                    elif k in ["CUSTOM_PATHS", "CUSTOM_ANTIGRAVITY_PATHS"] and v:
                        custom_paths = [p.strip() for p in v.split(":") if p.strip()]
        except Exception:
            pass

    # If configured path doesn't exist on disk, or wasn't set, auto-discover from installed engines
    if (not app_dir or not os.path.isdir(app_dir)) or (not ide_dir or not os.path.isdir(ide_dir)):
        if not detected_app or not detected_ide:
            for inst in scan_installations():
                if ('App' in inst['type'] or 'Manager' in inst['type']) and not detected_app:
                    detected_app = inst['path']
                elif 'IDE' in inst['type'] and not detected_ide:
                    detected_ide = inst['path']

    if app_dir and os.path.isdir(app_dir):
        final_app = app_dir
    elif detected_app and os.path.isdir(detected_app):
        final_app = detected_app
    elif app_dir:
        final_app = app_dir
    else:
        for cand in ["/opt/Antigravity-x64", "/opt/antigravity2", "/opt/antigravity"]:
            if os.path.isdir(cand):
                final_app = cand
                break
        else:
            final_app = "/opt/Antigravity-x64"

    if ide_dir and os.path.isdir(ide_dir):
        final_ide = ide_dir
    elif detected_ide and os.path.isdir(detected_ide):
        final_ide = detected_ide
    elif ide_dir:
        final_ide = ide_dir
    else:
        for cand in ["/opt/antigravity-ide", "/opt/antigravity", "/opt/antigravity2"]:
            if os.path.isdir(cand):
                final_ide = cand
                break
        else:
            final_ide = "/opt/antigravity-ide"

    return final_app, final_ide, custom_paths

def save_paths_config(app_dir, ide_dir, custom_paths=None):
    os.makedirs(CONF_DIR, exist_ok=True)
    if custom_paths is None:
        custom_paths = []
    filtered = [p for p in custom_paths if p and p != app_dir and p != ide_dir]
    custom_str = ":".join(filtered)
    with open(PATHS_CONF, "w", encoding="utf-8") as f:
        f.write("# Antigravity Suite Installation Paths Configuration\n")
        f.write(f'APP_INSTALL_DIR="{app_dir}"\n')
        f.write(f'IDE_INSTALL_DIR="{ide_dir}"\n')
        f.write(f'CUSTOM_ANTIGRAVITY_PATHS="{custom_str}"\n')

def create_launcher_and_desktop(cmd_name, app_type, exe_target, install_dir):
    local_bin = os.path.join(REAL_HOME, ".local", "bin")
    local_apps = os.path.join(REAL_HOME, ".local", "share", "applications")
    os.makedirs(local_bin, exist_ok=True)
    os.makedirs(local_apps, exist_ok=True)

    launcher_path = os.path.join(local_bin, cmd_name)
    desktop_path = os.path.join(local_apps, f"{cmd_name}.desktop")

    user_data_dir = os.path.join(REAL_HOME, ".config", f"Antigravity IDE-{cmd_name}" if "IDE" in app_type else f"Antigravity-{cmd_name}")
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write(f'exec "{exe_target}" --password-store=basic --user-data-dir="{user_data_dir}" --class="{cmd_name}" --name="{cmd_name}" "$@"\n')
    os.chmod(launcher_path, 0o755)

    icon_name = "antigravity-ide" if "IDE" in app_type else "antigravity-app"
    with open(desktop_path, "w", encoding="utf-8") as f:
        f.write("[Desktop Entry]\n")
        f.write(f"Name=Google Antigravity ({cmd_name})\n")
        f.write(f"Comment=Google Antigravity {app_type}\n")
        f.write(f"Exec={launcher_path} %U\n")
        f.write(f"Icon={icon_name}\n")
        f.write("Type=Application\n")
        f.write(f"StartupWMClass={cmd_name}\n")
        f.write("Categories=Development;IDE;\n")
        f.write("Terminal=false\n")
    os.chmod(desktop_path, 0o644)
    subprocess.run(["update-desktop-database", local_apps], check=False, stderr=subprocess.DEVNULL)
    print(f"{GREEN}[SUCCESS] Created launcher {launcher_path} and desktop entry {desktop_path}{NC}")

def toggle_keyring_for_path(install_dir):
    cache_f = os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable")
    is_normal = os.path.isfile(cache_f)
    print(f"\nCurrent Keyring Mode: {'Normal File Storage (Decoupled)' if is_normal else 'GNOME Keyring (Secret Service)'}")
    print("  [1] Switch to Normal File Storage (Bypasses GNOME Keyring - Recommended)")
    print("  [2] Switch to GNOME Keyring (Secret Service)")
    k_choice = input("Select storage mode [1-2]: ").strip()
    keyring_tool = os.path.join(REAL_HOME, ".local", "bin", "antigravity-keyring.py")
    if not os.path.isfile(keyring_tool):
        keyring_tool = os.path.join(os.path.dirname(__file__), "antigravity-keyring.py")
    if os.path.isfile(keyring_tool):
        mode = "normal" if k_choice == "1" else "gnome"
        subprocess.run([sys.executable, keyring_tool, "set", "all", mode], check=False)

def configure_single_installation(item, curr_app, curr_ide, custom_paths):
    while True:
        is_primary_app = (curr_app and os.path.realpath(item['path']) == os.path.realpath(curr_app))
        is_primary_ide = (curr_ide and os.path.realpath(item['path']) == os.path.realpath(curr_ide))
        if is_primary_app:
            role_label = f"{GREEN}[Primary App Target (Launched by antigravity-1 & antigravity-acc2)]{NC}"
        elif is_primary_ide:
            role_label = f"{GREEN}[Primary IDE Target (Launched by antigravity-ide)]{NC}"
        else:
            role_label = f"{YELLOW}[Secondary / Standalone Installation]{NC}"

        print(f"\n{CYAN}----------------------------------------------------------------------------------------{NC}")
        print(f"{BOLD}{CYAN}  Configuring: {item['type']} ({item['version']}) in {item['path']}{NC}")
        print(f"{CYAN}----------------------------------------------------------------------------------------{NC}")
        print(f"  • Type:               {item['type']}")
        print(f"  • Version:            {item['version']}")
        print(f"  • Directory Path:     {item['path']}")
        print(f"  • Executable:         {item['executable'] or 'None'}")
        print(f"  • Permissions:        {'Writable by current user (Ready)' if item['writable'] else 'Read-Only (Requires sudo/chown)'}")
        print(f"  • Suite Role:         {role_label}")
        print(f"----------------------------------------------------------------------------------------")
        print("Select setting to change for this installation:")
        print("  [1] Change / Relocate Installation Directory Path")
        print("  [2] Set as Suite Target (Set as Primary App or Primary IDE)")
        print("  [3] Re-generate Desktop Launcher & Shortcut for this Installation")
        print("  [4] Toggle Credential Storage Mode (Normal File Storage vs GNOME Keyring)")
        print("  [5] Download & Re-install Latest Binaries into this Directory")
        print("  [0] Done with this installation (Return to list)")
        print(f"{CYAN}----------------------------------------------------------------------------------------{NC}")
        try:
            sub_c = input(f"Select option [0-5, Default: 0]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if sub_c in ["0", "", "q", "exit"]:
            break
        elif sub_c == "1":
            old_p = item['path']
            new_p = input(f"\nEnter new directory path for this installation [current: {old_p}]: ").strip()
            if new_p and new_p != old_p:
                new_p = os.path.realpath(os.path.expanduser(new_p))
                if not os.path.isdir(new_p):
                    os.makedirs(new_p, exist_ok=True)
                old_has_files = (os.path.isfile(os.path.join(old_p, 'resources', 'app.asar')) or os.path.isfile(os.path.join(old_p, 'resources', 'app', 'product.json')))
                new_has_files = (os.path.isfile(os.path.join(new_p, 'resources', 'app.asar')) or os.path.isfile(os.path.join(new_p, 'resources', 'app', 'product.json')))
                if old_has_files and not new_has_files:
                    m_ans = input(f"Would you like to copy existing installation files from {old_p} to {new_p}? [Y/n]: ").strip().lower()
                    if m_ans not in ["n", "no"]:
                        print(f"Copying files from {old_p} to {new_p}...")
                        subprocess.run(["cp", "-a", f"{old_p}/.", f"{new_p}/"], check=False)
                item['path'] = new_p
                exe_name = os.path.basename(item['executable']) if item['executable'] else ('antigravity-ide' if 'IDE' in item['type'] else 'antigravity')
                item['executable'] = os.path.join(new_p, exe_name)
                item['writable'] = os.access(new_p, os.W_OK)
                if is_primary_app:
                    curr_app = new_p
                if is_primary_ide:
                    curr_ide = new_p
                if old_p in custom_paths:
                    custom_paths.remove(old_p)
                if new_p not in custom_paths and new_p not in [curr_app, curr_ide]:
                    custom_paths.append(new_p)
                print(f"{GREEN}[SUCCESS] Installation path updated to: {new_p}{NC}")
        elif sub_c == "2":
            print("\nSelect Suite Role:")
            print(f"  [1] Set as Primary App Target (Used by antigravity-1 & antigravity-acc2)")
            print(f"  [2] Set as Primary IDE Target (Used by antigravity-ide)")
            print(f"  [3] Clear Primary Target role (Keep as Secondary / Standalone)")
            r_ans = input("Choose role [1-3]: ").strip()
            if r_ans == "1":
                curr_app = item['path']
                print(f"{GREEN}[SUCCESS] Set {item['path']} as Primary App Target.{NC}")
            elif r_ans == "2":
                curr_ide = item['path']
                print(f"{GREEN}[SUCCESS] Set {item['path']} as Primary IDE Target.{NC}")
            elif r_ans == "3":
                if is_primary_app: curr_app = ""
                if is_primary_ide: curr_ide = ""
                print(f"{GREEN}[SUCCESS] Cleared primary role for {item['path']}.{NC}")
        elif sub_c == "3":
            def_name = re.sub(r'[^a-z0-9_-]+', '-', item['type'].lower())
            cmd_name = input(f"Enter launcher command name [default: {def_name}]: ").strip()
            cmd_name = cmd_name if cmd_name else def_name
            exe_target = item['executable'] if (item['executable'] and os.path.isfile(item['executable'])) else os.path.join(item['path'], 'antigravity-ide' if 'IDE' in item['type'] else 'antigravity')
            create_launcher_and_desktop(cmd_name, item['type'], exe_target, item['path'])
        elif sub_c == "4":
            toggle_keyring_for_path(item['path'])
        elif sub_c == "5":
            c_type = "ide" if "IDE" in item['type'] else "app"
            manage_sh = os.path.join(REAL_HOME, ".local", "bin", "manage-antigravity.sh")
            if not os.path.isfile(manage_sh):
                manage_sh = os.path.join(os.path.dirname(__file__), "manage-antigravity.sh")
            print(f"\n{CYAN}Downloading & installing fresh {item['type']} into {item['path']}...{NC}")
            flag = "--ide-dir" if c_type == "ide" else "--app-dir"
            subprocess.run(["bash", manage_sh, "install", c_type, flag, item['path']], check=False)

    return curr_app, curr_ide

def configure_paths_interactive(installs):
    curr_app, curr_ide, custom_paths = load_paths_config()

    while True:
        installs = scan_installations()
        print(f"\n{CYAN}========================================================================================{NC}")
        print(f"{BOLD}{CYAN}                    Installed Antigravity Suite Manager                                 {NC}")
        print(f"{CYAN}========================================================================================{NC}")
        print(f"{BOLD}Detected Antigravity Installations on System ({len(installs)} found):{NC}")
        print(f"----------------------------------------------------------------------------------------")
        if installs:
            for idx, item in enumerate(installs, 1):
                ver = f"v{item['version']}" if item['version'] != "Unknown" else "Unknown"
                tags = []
                if curr_app and os.path.realpath(item['path']) == os.path.realpath(curr_app):
                    tags.append(f"{GREEN}[Primary App Target]{NC}")
                if curr_ide and os.path.realpath(item['path']) == os.path.realpath(curr_ide):
                    tags.append(f"{GREEN}[Primary IDE Target]{NC}")
                tag_str = " ".join(tags)
                print(f"  [{idx}] {item['type']:<20} {ver:<10} in {item['path']} {tag_str}")
        else:
            print(f"  {YELLOW}None detected outside defaults.{NC}")
        print(f"----------------------------------------------------------------------------------------")
        print(f"  [C] Add / Register a Custom Antigravity Path")
        print(f"  [R] Reset Primary Targets to Defaults (/opt/antigravity2 & /opt/antigravity)")
        print(f"  [0] Done / Save & Continue")
        print(f"{CYAN}----------------------------------------------------------------------------------------{NC}")
        print(f"{BOLD}Which installed Antigravity do you want to configure or change?{NC}")
        try:
            choice = input(f"Select installation [1-{len(installs)}, C for custom, 0 to finish]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting configuration.")
            break

        if choice in ["0", "", "q", "exit"]:
            save_paths_config(curr_app, curr_ide, custom_paths)
            print(f"{GREEN}[SUCCESS] Saved configuration to {PATHS_CONF}{NC}")
            break
        elif choice.upper() == "C":
            custom_p = input("\nEnter custom path to Antigravity installation (or directory to install into): ").strip()
            if custom_p:
                custom_p = os.path.realpath(os.path.expanduser(custom_p))
                if not os.path.isdir(custom_p):
                    create_ans = input(f"Directory {custom_p} does not exist. Create it? [Y/n]: ").strip().lower()
                    if create_ans not in ["n", "no"]:
                        os.makedirs(custom_p, exist_ok=True)
                app_cand = inspect_app_dir(custom_p)
                ide_cand = inspect_ide_dir(custom_p)
                new_cand = None
                if app_cand:
                    new_cand = app_cand
                elif ide_cand:
                    new_cand = ide_cand
                else:
                    print("Directory does not contain an existing Antigravity binary yet.")
                    t_ans = input("Is this target for [1] Antigravity App or [2] Antigravity IDE? [Default: 1]: ").strip()
                    cand_type = "Antigravity IDE" if t_ans == "2" else "Antigravity App"
                    new_cand = {
                        'type': cand_type,
                        'version': 'Not installed yet',
                        'path': custom_p,
                        'executable': os.path.join(custom_p, 'antigravity-ide' if t_ans == "2" else 'antigravity'),
                        'writable': os.access(custom_p, os.W_OK)
                    }
                if custom_p not in custom_paths:
                    custom_paths.append(custom_p)
                save_paths_config(curr_app, curr_ide, custom_paths)
                print(f"{GREEN}[OK] Added {custom_p} to registered installations.{NC}")
                curr_app, curr_ide = configure_single_installation(new_cand, curr_app, curr_ide, custom_paths)
                save_paths_config(curr_app, curr_ide, custom_paths)
        elif choice.upper() == "R":
            curr_app = "/opt/antigravity2"
            curr_ide = "/opt/antigravity"
            save_paths_config(curr_app, curr_ide, custom_paths)
            print(f"{GREEN}[OK] Reset primary targets: App -> {curr_app}, IDE -> {curr_ide}{NC}")
        elif choice.isdigit() and 1 <= int(choice) <= len(installs):
            target = installs[int(choice) - 1]
            curr_app, curr_ide = configure_single_installation(target, curr_app, curr_ide, custom_paths)
            save_paths_config(curr_app, curr_ide, custom_paths)
        else:
            print(f"{RED}[ERROR] Invalid selection '{choice}'.{NC}")

def get_db_step_count(db_path):
    """Safely queries SQLite database step count for precedence comparison."""
    if not os.path.isfile(db_path):
        return -1
    try:
        import sqlite3
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as con:
            row = con.execute("SELECT count(*) FROM steps").fetchone()
            return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return -1

def safe_toggle_history_mode(is_ide, is_acc1, is_shared, p_dir, local_bin, REAL_HOME, name=""):
    """Safely toggles between Shared and Isolated history with automated backup and zero data loss."""
    if is_acc1:
        print(f"{YELLOW}[NOTICE] Account 1 is the Master Shared Pool and cannot be isolated.{NC}")
        return

    shared_pool = os.path.join(REAL_HOME, ".gemini", "antigravity")
    os.makedirs(os.path.join(shared_pool, "conversations"), exist_ok=True)
    os.makedirs(os.path.join(shared_pool, "brain"), exist_ok=True)

    # 1. ALWAYS create an automated restorable backup first
    migration_tool = os.path.join(local_bin, "antigravity-migration.py")
    if not os.path.isfile(migration_tool):
        migration_tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antigravity-migration.py")

    if os.path.isfile(migration_tool):
        safe_label = f"pre_toggle_{name or 'instance'}"
        subprocess.run([sys.executable, migration_tool, "create-backup", "--category", "history", "--label", safe_label], check=False)

    merge_script = os.path.join(local_bin, "antigravity-merge-history.py")
    if not os.path.isfile(merge_script):
        merge_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antigravity-merge-history.py")

    ts = int(datetime.datetime.now().timestamp())

    if is_ide:
        ide_root = os.path.join(p_dir, ".gemini", "antigravity-ide") if not p_dir.endswith("antigravity-ide") else p_dir
        os.makedirs(ide_root, exist_ok=True)
        ide_conv = os.path.join(ide_root, "conversations")
        ide_brain = os.path.join(ide_root, "brain")

        if is_shared:
            # Switching from Shared -> Isolated
            if os.path.islink(ide_conv):
                os.unlink(ide_conv)
            os.makedirs(ide_conv, exist_ok=True)

            copied = 0
            for db in glob.glob(os.path.join(shared_pool, "conversations", "*.db")):
                shutil.copy2(db, os.path.join(ide_conv, os.path.basename(db)))
                copied += 1

            if os.path.islink(ide_brain):
                os.unlink(ide_brain)
            os.makedirs(ide_brain, exist_ok=True)

            # Unlink shared summaries and make local copies so isolated IDE does not write to shared pool
            for sum_name in ["conversation_summaries.db", "conversation_summaries.db-wal", "conversation_summaries.db-shm", "agyhub_summaries_proto.pb"]:
                s_path = os.path.join(ide_root, sum_name)
                if os.path.islink(s_path):
                    try: os.unlink(s_path)
                    except Exception: pass
            for sum_f in glob.glob(os.path.join(shared_pool, "*summaries*")):
                try: shutil.copy2(sum_f, os.path.join(ide_root, os.path.basename(sum_f)))
                except Exception: pass

            print(f"{GREEN}[SUCCESS] Antigravity IDE history set to Isolated Private.{NC}")
            print(f"  • Existing {copied} conversations cloned locally to {ide_conv}.")
        else:
            # Switching from Isolated -> Shared
            copied = 0
            if os.path.isdir(ide_conv) and not os.path.islink(ide_conv):
                for db in glob.glob(os.path.join(ide_conv, "*.db")):
                    dst = os.path.join(shared_pool, "conversations", os.path.basename(db))
                    should_copy = False
                    if not os.path.exists(dst):
                        should_copy = True
                    else:
                        c_steps = get_db_step_count(db)
                        dst_steps = get_db_step_count(dst)
                        if c_steps > dst_steps:
                            should_copy = True
                        elif c_steps == dst_steps and os.path.getmtime(db) > os.path.getmtime(dst):
                            should_copy = True
                    if should_copy:
                        shutil.copy2(db, dst)
                        copied += 1
                try:
                    os.rename(ide_conv, f"{ide_conv}.bak_{ts}")
                except Exception:
                    pass

            if os.path.isdir(ide_brain) and not os.path.islink(ide_brain):
                for b in glob.glob(os.path.join(ide_brain, "*")):
                    dst_b = os.path.join(shared_pool, "brain", os.path.basename(b))
                    if os.path.isdir(b):
                        shutil.copytree(b, dst_b, dirs_exist_ok=True)
                    else:
                        shutil.copy2(b, dst_b)
                try:
                    os.rename(ide_brain, f"{ide_brain}.bak_{ts}")
                except Exception:
                    pass

            if not os.path.islink(ide_conv):
                os.symlink(os.path.join(shared_pool, "conversations"), ide_conv)
            if not os.path.islink(ide_brain):
                os.symlink(os.path.join(shared_pool, "brain"), ide_brain)
            
            for sum_name in ["conversation_summaries.db", "agyhub_summaries_proto.pb"]:
                sum_link = os.path.join(ide_root, sum_name)
                if not os.path.islink(sum_link):
                    if os.path.isfile(sum_link):
                        try: os.rename(sum_link, f"{sum_link}.bak_{ts}")
                        except Exception: pass
                    master_sum = os.path.join(shared_pool, sum_name)
                    if os.path.isfile(master_sum):
                        os.symlink(master_sum, sum_link)

            if os.path.isfile(merge_script):
                subprocess.run([sys.executable, merge_script, "--master", shared_pool, "--quiet"], check=False)

            print(f"{GREEN}[SUCCESS] Antigravity IDE history merged and linked to Shared 3-Way Sync.{NC}")
            print(f"  • {copied} private conversations merged into master pool.")
    else:
        # App Clone
        target_link = os.path.join(p_dir, ".gemini", "antigravity")
        if is_shared:
            # Switching from Shared -> Isolated
            if os.path.islink(target_link):
                os.unlink(target_link)
            iso_conv = os.path.join(target_link, "conversations")
            iso_brain = os.path.join(target_link, "brain")
            os.makedirs(iso_conv, exist_ok=True)
            os.makedirs(iso_brain, exist_ok=True)

            copied = 0
            for db in glob.glob(os.path.join(shared_pool, "conversations", "*.db")):
                shutil.copy2(db, os.path.join(iso_conv, os.path.basename(db)))
                copied += 1

            for sum_f in glob.glob(os.path.join(shared_pool, "*summaries*")):
                shutil.copy2(sum_f, os.path.join(target_link, os.path.basename(sum_f)))

            print(f"{GREEN}[SUCCESS] Clone history set to Isolated Private.{NC}")
            print(f"  • Existing {copied} conversations cloned locally to {iso_conv}.")
        else:
            # Switching from Isolated -> Shared
            copied = 0
            if os.path.isdir(target_link) and not os.path.islink(target_link):
                c_conv = os.path.join(target_link, "conversations")
                if os.path.isdir(c_conv):
                    for db in glob.glob(os.path.join(c_conv, "*.db")):
                        dst = os.path.join(shared_pool, "conversations", os.path.basename(db))
                        should_copy = False
                        if not os.path.exists(dst):
                            should_copy = True
                        else:
                            c_steps = get_db_step_count(db)
                            dst_steps = get_db_step_count(dst)
                            if c_steps > dst_steps:
                                should_copy = True
                            elif c_steps == dst_steps and os.path.getmtime(db) > os.path.getmtime(dst):
                                should_copy = True
                        if should_copy:
                            shutil.copy2(db, dst)
                            copied += 1
                c_brain = os.path.join(target_link, "brain")
                if os.path.isdir(c_brain):
                    for b in glob.glob(os.path.join(c_brain, "*")):
                        dst_b = os.path.join(shared_pool, "brain", os.path.basename(b))
                        if os.path.isdir(b):
                            shutil.copytree(b, dst_b, dirs_exist_ok=True)
                        else:
                            shutil.copy2(b, dst_b)
                try:
                    os.rename(target_link, f"{target_link}.bak_{ts}")
                except Exception:
                    pass

            os.makedirs(os.path.dirname(target_link), exist_ok=True)
            if not os.path.islink(target_link):
                os.symlink(shared_pool, target_link)

            if os.path.isfile(merge_script):
                subprocess.run([sys.executable, merge_script, "--master", shared_pool, "--quiet"], check=False)

            print(f"{GREEN}[SUCCESS] Clone history merged and linked to Shared 3-Way Sync.{NC}")
            print(f"  • {copied} private conversations merged into master pool.")

def configure_single_clone(clone):
    while True:
        local_bin = os.path.join(REAL_HOME, ".local", "bin")
        local_apps = os.path.join(REAL_HOME, ".local", "share", "applications")

        cid = clone['id']
        p_dir = clone['profile_dir']
        is_acc1 = (cid == 'app1')
        is_acc2 = (cid == 'app2')
        is_ide1 = (cid == 'ide1')

        # Check history sync
        if is_acc1:
            h_mode = "Primary Master Pool (Shared with all accounts)"
            is_shared = True
        elif is_ide1:
            h_link = os.path.join(p_dir, "conversations")
            is_shared = os.path.islink(h_link)
            h_mode = "Shared 3-Way Sync" if is_shared else "Isolated Private"
        else:
            h_link = os.path.join(p_dir, ".gemini", "antigravity")
            is_shared = os.path.islink(h_link)
            h_mode = "Shared 3-Way Sync" if is_shared else "Isolated Private"

        # Check keyring
        cache_f = os.path.join(p_dir, ".gemini", "cache", "antigravity-keyring-unavailable")
        if is_acc1:
            cache_f = os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable")
        elif is_ide1:
            cache_f = os.path.join(REAL_HOME, '.gemide', 'cache', 'antigravity-keyring-unavailable')
            if not os.path.isfile(cache_f):
                cache_f = os.path.join(REAL_HOME, '.gemini', 'antigravity-ide', 'cache', 'antigravity-keyring-unavailable')
        is_normal_keyring = os.path.isfile(cache_f)
        k_mode = "Normal (File Storage - Recommended)" if is_normal_keyring else "GNOME Keyring (Secret Service)"

        # Check process
        running = False
        if is_acc1:
            running = is_acc1_running(REAL_HOME)
        elif is_acc2:
            running = subprocess.run(["pgrep", "-f", "antigravity-profile2.*Antigravity"], capture_output=True).returncode == 0
        elif is_ide1:
            running = is_main_ide_running(REAL_HOME)
        else:
            bname = os.path.basename(p_dir)
            running = subprocess.run(["pgrep", "-f", f"{bname}"], capture_output=True).returncode == 0

        launcher_f = clone['launcher']
        linked_bin = get_launcher_binary(launcher_f) if (launcher_f and os.path.isfile(launcher_f)) else "Default System Binary"
        if launcher_f and os.path.isfile(launcher_f) and (not linked_bin or not os.path.isfile(linked_bin)):
            cand_exes = ["/opt/antigravity-ide/antigravity-ide", "/opt/antigravity/antigravity-ide"] if is_ide1 else ["/opt/Antigravity-x64/antigravity", "/opt/antigravity2/antigravity", "/opt/antigravity/antigravity"]
            for ce in cand_exes:
                if os.path.isfile(ce):
                    update_launcher_binary(launcher_f, ce)
                    linked_bin = ce
                    break

        print(f"\n{CYAN}----------------------------------------------------------------------------------------{NC}")
        print(f"{BOLD}{CYAN}  Configuring Account / Clone: {clone['name']}{NC}")
        print(f"{CYAN}----------------------------------------------------------------------------------------{NC}")
        print(f"  • Instance ID:        {cid}")
        print(f"  • Type & Role:        {clone['type']} ({clone['role']})")
        print(f"  • Profile Directory:  {p_dir}")
        print(f"  • Launcher Script:    {launcher_f}")
        print(f"  • Desktop File:       {clone['desktop']}")
        print(f"  • Window Class:       {clone['wm_class']}")
        print(f"  • Linked Binary:      {linked_bin or 'Default'}")
        print(f"  • History Sync Mode:  {GREEN if is_shared else YELLOW}{h_mode}{NC}")
        print(f"  • Credential Storage: {GREEN if is_normal_keyring else BLUE}{k_mode}{NC}")
        print(f"  • Process Status:     {GREEN}Running{NC}" if running else "Stopped")
        print(f"----------------------------------------------------------------------------------------")
        print("Select setting to modify:")
        print("  [1] Toggle History Sharing Mode (Shared 3-Way Sync vs Isolated Private)")
        print("  [2] Toggle Credential Storage Mode (Normal File Storage vs GNOME Keyring)")
        print("  [3] Change Linked Antigravity Binary / Engine Executable")
        print("  [4] Re-generate Desktop Launcher & Icons")
        print("  [5] Relocate / Rename Profile Directory")
        if is_ide1:
            print("  [6] Create Additional IDE Clone / Profile")
        elif is_acc1:
            print("  [6] Create Additional App Account Profile (Account 2 / Custom)")
        else:
            print("  [6] Delete / Remove this Clone")
        print("  [0] Done with this clone (Return to Control Center)")
        print(f"{CYAN}----------------------------------------------------------------------------------------{NC}")

        try:
            choice = input(f"Select option [0-6, Default: 0]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice in ["0", "", "q", "exit"]:
            break
        elif choice == "1":
            is_target_ide = is_ide1 or ('ide' in cid) or ('IDE' in clone.get('type', ''))
            safe_toggle_history_mode(is_target_ide, is_acc1, is_shared, p_dir, local_bin, REAL_HOME, name=cid)
        elif choice == "2":
            keyring_tool = os.path.join(local_bin, "antigravity-keyring.py")
            if not os.path.isfile(keyring_tool):
                keyring_tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antigravity-keyring.py")
            new_mode = "gnome" if is_normal_keyring else "normal"
            if is_acc1:
                subprocess.run([sys.executable, keyring_tool, "set", "app1", new_mode], check=False)
            elif cid == "app2":
                subprocess.run([sys.executable, keyring_tool, "set", "app2", new_mode], check=False)
            elif 'ide' in cid:
                subprocess.run([sys.executable, keyring_tool, "set", "ide", new_mode], check=False)
            else:
                os.makedirs(os.path.dirname(cache_f), exist_ok=True)
                if is_normal_keyring:
                    try: os.remove(cache_f)
                    except Exception: pass
                    if launcher_f and os.path.isfile(launcher_f):
                        with open(launcher_f, "r") as lf: content = lf.read()
                        content = content.replace("--password-store=basic ", "").replace("--password-store=basic", "")
                        with open(launcher_f, "w") as lf: lf.write(content)
                else:
                    with open(cache_f, "w") as f: f.write("# Keyring bypassed\n")
                    if launcher_f and os.path.isfile(launcher_f):
                        with open(launcher_f, "r") as lf: content = lf.read()
                        if "--password-store=basic" not in content:
                            lines = content.splitlines()
                            new_lines = []
                            for line in lines:
                                if line.strip().startswith("exec "):
                                    m = re.match(r'^(\s*exec\s+("[^"]+"|\'[^\']+\'|\S+))(.*)$', line)
                                    if m:
                                        line = f'{m.group(1)} --password-store=basic{m.group(3)}'
                                new_lines.append(line)
                            content = "\n".join(new_lines) + "\n"
                            with open(launcher_f, "w") as lf: lf.write(content)
            print(f"{GREEN}[SUCCESS] Switched credential mode to {new_mode.upper()}.{NC}")
        elif choice == "3":
            if not os.path.isfile(launcher_f):
                print(f"{RED}[ERROR] Launcher script {launcher_f} does not exist.{NC}")
                continue
            installs = scan_installations()
            print("\nSelect engine binary to link to this clone:")
            valid_bins = []
            for inst in installs:
                exe = inst['executable']
                if exe and os.path.isfile(exe):
                    valid_bins.append((inst['type'], inst['version'], exe))
                    print(f"  [{len(valid_bins)}] {inst['type']} ({inst['version']}) -> {exe}")
            print(f"  [C] Enter custom binary executable path")
            b_ans = input(f"Select choice [1-{len(valid_bins)}, C]: ").strip()
            new_exe = ""
            if b_ans.isdigit() and 1 <= int(b_ans) <= len(valid_bins):
                new_exe = valid_bins[int(b_ans) - 1][2]
            elif b_ans.upper() == "C":
                custom_exe = input("Enter full path to executable: ").strip()
                if os.path.isfile(os.path.expanduser(custom_exe)):
                    new_exe = os.path.realpath(os.path.expanduser(custom_exe))
            if new_exe:
                if update_launcher_binary(launcher_f, new_exe):
                    print(f"{GREEN}[SUCCESS] Updated launcher {launcher_f} to execute: {new_exe}{NC}")
                else:
                    print(f"{RED}[ERROR] Failed to update launcher file.{NC}")
        elif choice == "4":
            manage_sh = os.path.join(local_bin, "manage-antigravity.sh")
            if not os.path.isfile(manage_sh):
                manage_sh = os.path.join(os.path.dirname(__file__), "manage-antigravity.sh")
            if os.path.isfile(manage_sh):
                ico_custom = input(f"Customize Icon appearance (Background & Colors) for {clone['name']}? [y/N]: ").strip().lower()
                if ico_custom in ["y", "yes"]:
                    if is_ide1:
                        subprocess.run(["bash", manage_sh, "set-icons", "ide"], check=False)
                    elif is_acc2:
                        subprocess.run(["bash", manage_sh, "set-icons", "app2"], check=False)
                    elif is_acc1:
                        subprocess.run(["bash", manage_sh, "set-icons", "app1"], check=False)
                    else:
                        subprocess.run(["bash", manage_sh, "set-icons"], check=False)
                if is_acc2:
                    subprocess.run(["bash", manage_sh, "app2"], check=False)
                elif is_acc1:
                    subprocess.run(["bash", manage_sh, "app1"], check=False)
                elif is_ide1:
                    subprocess.run(["bash", manage_sh, "ide-shortcuts"], check=False)
            if launcher_f and os.path.isfile(launcher_f):
                cur_bin = get_launcher_binary(launcher_f)
                if not cur_bin or not os.path.isfile(cur_bin):
                    cand_exes = ["/opt/antigravity-ide/antigravity-ide", "/opt/antigravity/antigravity-ide"] if is_ide1 else ["/opt/Antigravity-x64/antigravity", "/opt/antigravity2/antigravity"]
                    for ce in cand_exes:
                        if os.path.isfile(ce):
                            update_launcher_binary(launcher_f, ce)
                            break
            has_other_apps = os.path.isdir(os.path.join(REAL_HOME, ".antigravity-profile2")) or \
                             os.path.isfile(os.path.join(local_bin, "antigravity-acc2")) or \
                             bool(glob.glob(os.path.join(REAL_HOME, ".antigravity-profile-app-*")))
            dup_dt = os.path.join(local_apps, "antigravity.desktop" if has_other_apps else "antigravity-1.desktop")
            try: os.remove(dup_dt)
            except Exception: pass
            subprocess.run(["update-desktop-database", local_apps], check=False, stderr=subprocess.DEVNULL)
            print(f"{GREEN}[SUCCESS] Regenerated desktop launcher and icons.{NC}")
        elif choice == "5":
            if is_acc1:
                print(f"{YELLOW}[NOTICE] Account 1 profile (~/.gemini) cannot be relocated.{NC}")
                continue
            if is_acc2:
                print(f"{YELLOW}[NOTICE] Standard Account 2 profile (~/.antigravity-profile2) cannot be relocated.{NC}")
                continue
            new_p = input(f"Enter new path for profile directory [current: {p_dir}]: ").strip()
            if new_p and new_p != p_dir:
                new_p = os.path.realpath(os.path.expanduser(new_p))
                os.makedirs(os.path.dirname(new_p), exist_ok=True)
                shutil.move(p_dir, new_p)
                if os.path.isfile(launcher_f):
                    update_launcher_profile_path(launcher_f, is_acc2, p_dir, new_p)
                clone['profile_dir'] = new_p
                print(f"{GREEN}[SUCCESS] Profile directory moved to {new_p} and launcher updated.{NC}")
        elif choice == "6":
            manage_sh = os.path.join(local_bin, "manage-antigravity.sh")
            if not os.path.isfile(manage_sh):
                manage_sh = os.path.join(os.path.dirname(__file__), "manage-antigravity.sh")
            if is_ide1:
                print(f"\n{CYAN}--- Create Additional IDE Clone / Profile ---{NC}")
                if os.path.isfile(manage_sh):
                    subprocess.run(["bash", manage_sh, "create-instance", "ide"], check=False)
                break
            elif is_acc1:
                print(f"\n{CYAN}--- Create Additional App Account Profile ---{NC}")
                print("  [1] Standard Account 2 (antigravity-acc2)")
                print("  [2] Custom App Profile (Named instance)")
                sub_c = input("Choose option [1-2, Default: 1]: ").strip()
                if sub_c == "2":
                    subprocess.run(["bash", manage_sh, "create-instance", "app"], check=False)
                else:
                    subprocess.run(["bash", manage_sh, "app2"], check=False)
                subprocess.run(["bash", manage_sh, "app1"], check=False)
                break
            else:
                c_confirm = input(f"Are you sure you want to delete clone '{clone['name']}'? [y/N]: ").strip().lower()
                if c_confirm in ["y", "yes"]:
                    if os.path.isfile(launcher_f):
                        try: os.remove(launcher_f)
                        except Exception: pass
                    if os.path.isfile(clone['desktop']):
                        try: os.remove(clone['desktop'])
                        except Exception: pass
                    d_prof = input(f"Also delete profile directory '{p_dir}' and its settings? [y/N]: ").strip().lower()
                    if d_prof in ["y", "yes"]:
                        shutil.rmtree(p_dir, ignore_errors=True)
                    subprocess.run(["update-desktop-database", local_apps], check=False, stderr=subprocess.DEVNULL)
                    if is_acc2 or 'app-' in cid:
                        subprocess.run(["bash", manage_sh, "app1"], check=False)
                    print(f"{GREEN}[SUCCESS] Clone '{clone['name']}' removed.{NC}")
                    break

def get_unified_instances():
    engines = scan_installations()
    engines_by_path = {os.path.realpath(eng['path']): eng for eng in engines}

    first_app = ""
    first_ide = ""
    for eng in engines:
        if ('App' in eng['type'] or 'Manager' in eng['type']) and not first_app:
            first_app = eng['path']
        elif 'IDE' in eng['type'] and not first_ide:
            first_ide = eng['path']

    curr_app, curr_ide, custom_paths = load_paths_config(first_app, first_ide)
    if (not curr_app or not os.path.isdir(curr_app)) and first_app:
        curr_app = first_app
    if (not curr_ide or not os.path.isdir(curr_ide)) and first_ide:
        curr_ide = first_ide

    clones = scan_clones(curr_app, curr_ide)

    unified = []

    for c in clones:
        launcher_f = c['launcher']
        linked_bin = get_launcher_binary(launcher_f) if (launcher_f and os.path.isfile(launcher_f)) else ""
        eng = None
        if linked_bin and os.path.isfile(linked_bin):
            eng_dir = os.path.realpath(os.path.dirname(linked_bin))
            if os.path.basename(eng_dir) in ['bin', 'MacOS']:
                eng_dir = os.path.dirname(eng_dir)
            eng = engines_by_path.get(eng_dir)
            if not eng:
                eng = inspect_ide_dir(eng_dir) or inspect_app_dir(eng_dir)
                if eng:
                    engines_by_path[eng_dir] = eng

        if not eng:
            if 'IDE' in c['type']:
                eng = engines_by_path.get(os.path.realpath(curr_ide))
                if not eng and os.path.isdir(curr_ide):
                    eng = inspect_ide_dir(os.path.realpath(curr_ide))
            else:
                eng = engines_by_path.get(os.path.realpath(curr_app))
                if not eng and os.path.isdir(curr_app):
                    eng = inspect_app_dir(os.path.realpath(curr_app))

        eng_path = eng['path'] if eng else (curr_ide if 'IDE' in c['type'] else curr_app)
        eng_ver = eng['version'] if eng else "Unknown"

        # Auto-heal launcher if the linked binary does not exist or is broken
        if launcher_f and os.path.isfile(launcher_f):
            if (not linked_bin or not os.path.isfile(linked_bin)) and eng and eng.get('executable') and os.path.isfile(eng['executable']):
                update_launcher_binary(launcher_f, eng['executable'])
                linked_bin = eng['executable']

        # Exclude phantom clones where engine does not exist on disk AND launcher does not exist
        if not eng and not os.path.isfile(launcher_f) and not os.path.isdir(eng_path):
            continue

        unified.append({
            'kind': 'instance',
            'clone': c,
            'engine': eng,
            'name': c['name'],
            'type': c['type'],
            'version': eng_ver,
            'engine_path': eng_path,
            'history_mode': c['history_mode'],
            'keyring_mode': c['keyring_mode'],
            'launcher': c['launcher'],
            'status': c['status']
        })

    used_engine_paths = {os.path.realpath(u['engine_path']) for u in unified if u.get('engine_path') and os.path.isdir(u.get('engine_path'))}
    for eng in engines:
        real_ep = os.path.realpath(eng['path'])
        if real_ep not in used_engine_paths:
            unified.append({
                'kind': 'engine',
                'clone': None,
                'engine': eng,
                'name': f"{eng['type']} (Standalone Engine)",
                'type': eng['type'],
                'version': eng['version'],
                'engine_path': eng['path'],
                'history_mode': 'N/A',
                'keyring_mode': 'Normal',
                'launcher': eng.get('executable', ''),
                'status': 'Installed'
            })

    def sort_order(item):
        cid = item.get('clone', {}).get('id', '') if item.get('clone') else ''
        if cid == 'ide1': return 0
        if cid == 'app1': return 1
        if cid == 'app2': return 2
        if cid.startswith('app-'): return 3
        if cid.startswith('ide-'): return 4
        return 5

    unified.sort(key=sort_order)
    return unified, curr_app, curr_ide, custom_paths

def configure_unified_instance(u_item, curr_app, curr_ide, custom_paths):
    local_bin = os.path.join(REAL_HOME, ".local", "bin")
    local_apps = os.path.join(REAL_HOME, ".local", "share", "applications")
    manage_sh = os.path.join(local_bin, "manage-antigravity.sh")
    if not os.path.isfile(manage_sh):
        manage_sh = os.path.join(os.path.dirname(__file__), "manage-antigravity.sh")

    while True:
        c = u_item.get('clone')
        eng = u_item.get('engine')
        cid = c['id'] if c else ""
        p_dir = c['profile_dir'] if c else ""
        is_acc1 = (cid == 'app1')
        is_acc2 = (cid == 'app2')
        is_ide1 = (cid == 'ide1')

        if c:
            if is_acc1:
                h_mode = "Master Shared Pool (Source of Truth)"
                is_shared = True
            elif is_ide1:
                h_link = os.path.join(p_dir, "conversations")
                is_shared = os.path.islink(h_link)
                h_mode = "Shared 3-Way Sync" if is_shared else "Isolated Private"
            else:
                h_link = os.path.join(p_dir, ".gemini", "antigravity")
                is_shared = os.path.islink(h_link)
                h_mode = "Shared 3-Way Sync" if is_shared else "Isolated Private"
        else:
            h_mode = "N/A (Standalone Engine)"
            is_shared = False

        if c:
            cache_f = os.path.join(p_dir, ".gemini", "cache", "antigravity-keyring-unavailable")
            if is_acc1:
                cache_f = os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable")
            elif is_ide1:
                cache_f = os.path.join(REAL_HOME, '.gemide', 'cache', 'antigravity-keyring-unavailable')
                if not os.path.isfile(cache_f):
                    cache_f = os.path.join(REAL_HOME, '.gemini', 'antigravity-ide', 'cache', 'antigravity-keyring-unavailable')
            is_normal_keyring = os.path.isfile(cache_f)
            k_mode = "Normal (File Storage - Recommended)" if is_normal_keyring else "GNOME Keyring (Secret Service)"
        else:
            cache_f = os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable")
            is_normal_keyring = os.path.isfile(cache_f)
            k_mode = "Normal (File Storage)" if is_normal_keyring else "GNOME Keyring"

        running = False
        if c:
            if is_acc1:
                running = is_acc1_running(REAL_HOME)
            elif is_acc2:
                running = subprocess.run(["pgrep", "-f", "antigravity-profile2.*Antigravity"], capture_output=True).returncode == 0
            elif is_ide1:
                running = is_main_ide_running(REAL_HOME)
            else:
                bname = os.path.basename(p_dir)
                running = subprocess.run(["pgrep", "-f", f"{bname}"], capture_output=True).returncode == 0

        launcher_f = c['launcher'] if c else ""
        linked_bin = get_launcher_binary(launcher_f) if (launcher_f and os.path.isfile(launcher_f)) else ""
        eng_p = u_item.get('engine_path', '')
        eng_v = u_item.get('version', 'Unknown')
        fresh_eng = inspect_ide_dir(eng_p) if (u_item.get('type') and 'IDE' in u_item['type']) else inspect_app_dir(eng_p)
        if fresh_eng:
            eng = fresh_eng
            eng_v = fresh_eng.get('version', 'Unknown')
            u_item['version'] = eng_v

        # Auto-heal launcher if the linked binary does not exist or is broken
        if launcher_f and os.path.isfile(launcher_f):
            if (not linked_bin or not os.path.isfile(linked_bin)) and eng and eng.get('executable') and os.path.isfile(eng['executable']):
                update_launcher_binary(launcher_f, eng['executable'])
                linked_bin = eng['executable']

        is_primary_app = (curr_app and os.path.realpath(eng_p) == os.path.realpath(curr_app))
        is_primary_ide = (curr_ide and os.path.realpath(eng_p) == os.path.realpath(curr_ide))
        if is_primary_app:
            role_label = f"{GREEN}[Primary App Target]{NC}"
        elif is_primary_ide:
            role_label = f"{GREEN}[Primary IDE Target]{NC}"
        else:
            role_label = f"{YELLOW}[Secondary Target]{NC}"

        print(f"\n{CYAN}----------------------------------------------------------------------------------------{NC}")
        print(f"{BOLD}{CYAN}  Configuring: {u_item['name']} [{u_item['type']}]{NC}")
        print(f"{CYAN}----------------------------------------------------------------------------------------{NC}")
        if c:
            print(f"  • Profile Directory:   {p_dir}")
            print(f"  • Launcher Script:     {launcher_f}")
            print(f"  • Desktop File:        {c.get('desktop', 'None')}")
            print(f"  • Window Class:        {c.get('wm_class', 'None')}")
            print(f"  • History Sync Mode:   {GREEN if is_shared else YELLOW}{h_mode}{NC}")
            print(f"  • Credential Storage:  {GREEN if is_normal_keyring else BLUE}{k_mode}{NC}")
            print(f"  • Process Status:      {GREEN}Running{NC}" if running else "  • Process Status:      Stopped")
        print(f"  • Engine Directory:    {eng_p} (v{eng_v}) {role_label}")
        print(f"  • Executable Binary:   {linked_bin or (eng.get('executable') if eng else 'Default')}")
        print(f"----------------------------------------------------------------------------------------")

        if c:
            print(f"{BOLD}Profile & Account Settings:{NC}")
            print("  [1] Toggle History Sharing Mode (Shared 3-Way Sync vs Isolated Private)")
            print("  [2] Toggle Credential Storage Mode (Normal File Storage vs GNOME Keyring)")
            print("  [3] Change Linked Antigravity Binary / Executable")
            print("  [4] Re-generate Desktop Launcher & Icons")
            print("  [5] Relocate / Rename Profile Directory")
            if is_ide1:
                print("  [6] Create Additional IDE Clone / Profile")
            elif is_acc1:
                print("  [6] Create Additional App Account Profile (Account 2 / Custom)")
            else:
                print("  [6] Delete / Remove this Clone Profile")
            print(f"\n{BOLD}Engine & Installation Settings:{NC}")
            print(f"  [7] Change / Relocate Engine Directory Path ({eng_p})")
            print(f"  [8] Download & Re-install Latest Binaries into Engine Path")
            print(f"  [9] Set Engine as Suite Primary Target (Primary App / IDE)")
            print(f"  [R] Apply RTL Patch to this Engine ({eng_p})")
            if "IDE" not in u_item.get('type', ''):
                print(f"  [F] Apply F5 Backend Reload & Isolation Patch ({eng_p})")
            print(f"  [0] Done with this instance (Return to Control Center)")
        else:
            print(f"{BOLD}Engine & Installation Settings:{NC}")
            print("  [1] Change / Relocate Installation Directory Path")
            print("  [2] Set as Suite Target (Primary App or Primary IDE)")
            print("  [3] Re-generate Desktop Launcher & Shortcut for this Installation")
            print("  [4] Toggle Credential Storage Mode (Normal File Storage vs GNOME Keyring)")
            print("  [5] Download & Re-install Latest Binaries into this Directory")
            print(f"  [R] Apply RTL Patch to this Engine ({eng_p})")
            if "IDE" not in u_item.get('type', ''):
                print(f"  [F] Apply F5 Backend Reload & Isolation Patch ({eng_p})")
            print("  [0] Done with this installation (Return to Control Center)")
        print(f"{CYAN}----------------------------------------------------------------------------------------{NC}")

        try:
            choice = input("Select option [Default: 0]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice in ["0", "", "q", "exit"]:
            break

        if c:
            is_target_ide = is_ide1 or ('ide' in cid) or ('IDE' in u_item.get('type', ''))
            if choice == "1":
                safe_toggle_history_mode(is_target_ide, is_acc1, is_shared, p_dir, local_bin, REAL_HOME, name=cid)
            elif choice == "2":
                keyring_tool = os.path.join(local_bin, "antigravity-keyring.py")
                if not os.path.isfile(keyring_tool):
                    keyring_tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antigravity-keyring.py")
                new_mode = "gnome" if is_normal_keyring else "normal"
                if is_acc1:
                    subprocess.run([sys.executable, keyring_tool, "set", "app1", new_mode], check=False)
                elif cid == "app2":
                    subprocess.run([sys.executable, keyring_tool, "set", "app2", new_mode], check=False)
                elif is_target_ide:
                    subprocess.run([sys.executable, keyring_tool, "set", "ide", new_mode], check=False)
                else:
                    os.makedirs(os.path.dirname(cache_f), exist_ok=True)
                    if is_normal_keyring:
                        try: os.remove(cache_f)
                        except Exception: pass
                        if launcher_f and os.path.isfile(launcher_f):
                            with open(launcher_f, "r") as lf: content = lf.read()
                            content = content.replace("--password-store=basic ", "").replace("--password-store=basic", "")
                            with open(launcher_f, "w") as lf: lf.write(content)
                        print(f"{GREEN}[SUCCESS] Switched credential mode to GNOME Keyring.{NC}")
                    else:
                        with open(cache_f, "w") as f: f.write("# Keyring bypassed\n")
                        if launcher_f and os.path.isfile(launcher_f):
                            with open(launcher_f, "r") as lf: content = lf.read()
                            if "--password-store=basic" not in content:
                                lines = content.splitlines()
                                new_lines = []
                                for line in lines:
                                    if line.strip().startswith("exec "):
                                        m = re.match(r'^(\s*exec\s+("[^"]+"|\'[^\']+\'|\S+))(.*)$', line)
                                        if m:
                                            line = f'{m.group(1)} --password-store=basic{m.group(3)}'
                                    new_lines.append(line)
                                content = "\n".join(new_lines) + "\n"
                                with open(launcher_f, "w") as lf: lf.write(content)
                        print(f"{GREEN}[SUCCESS] Switched credential mode to Normal File Storage (Keyring bypassed).{NC}")
            elif choice == "3":
                if not os.path.isfile(launcher_f):
                    print(f"{RED}[ERROR] Launcher script {launcher_f} does not exist.{NC}")
                    continue
                installs = scan_installations()
                print("\nSelect engine binary to link to this instance:")
                valid_bins = []
                for inst in installs:
                    exe = inst['executable']
                    if exe and os.path.isfile(exe):
                        valid_bins.append((inst['type'], inst['version'], exe))
                        print(f"  [{len(valid_bins)}] {inst['type']} ({inst['version']}) -> {exe}")
                print(f"  [C] Enter custom binary executable path")
                b_ans = input(f"Select choice [1-{len(valid_bins)}, C]: ").strip()
                new_exe = ""
                if b_ans.isdigit() and 1 <= int(b_ans) <= len(valid_bins):
                    new_exe = valid_bins[int(b_ans) - 1][2]
                elif b_ans.upper() == "C":
                    custom_exe = input("Enter full path to executable: ").strip()
                    if os.path.isfile(os.path.expanduser(custom_exe)):
                        new_exe = os.path.realpath(os.path.expanduser(custom_exe))
                if new_exe:
                    if update_launcher_binary(launcher_f, new_exe):
                        print(f"{GREEN}[SUCCESS] Updated launcher {launcher_f} to execute: {new_exe}{NC}")
                    else:
                        print(f"{RED}[ERROR] Failed to update launcher file.{NC}")
            elif choice == "4":
                if os.path.isfile(manage_sh):
                    ico_custom = input(f"Customize Icon appearance (Background & Colors) for {u_item['name']}? [y/N]: ").strip().lower()
                    if ico_custom in ["y", "yes"]:
                        if is_ide1:
                            subprocess.run(["bash", manage_sh, "set-icons", "ide"], check=False)
                        elif is_acc2:
                            subprocess.run(["bash", manage_sh, "set-icons", "app2"], check=False)
                        elif is_acc1:
                            subprocess.run(["bash", manage_sh, "set-icons", "app1"], check=False)
                        else:
                            subprocess.run(["bash", manage_sh, "set-icons"], check=False)
                    if is_acc2: subprocess.run(["bash", manage_sh, "app2"], check=False)
                    elif is_acc1: subprocess.run(["bash", manage_sh, "app1"], check=False)
                    elif is_ide1: subprocess.run(["bash", manage_sh, "ide-shortcuts"], check=False)
                if launcher_f and os.path.isfile(launcher_f):
                    cur_bin = get_launcher_binary(launcher_f)
                    if (not cur_bin or not os.path.isfile(cur_bin)) and eng and eng.get('executable') and os.path.isfile(eng['executable']):
                        update_launcher_binary(launcher_f, eng['executable'])
                has_other_apps = os.path.isdir(os.path.join(REAL_HOME, ".antigravity-profile2")) or \
                                 os.path.isfile(os.path.join(local_bin, "antigravity-acc2")) or \
                                 bool(glob.glob(os.path.join(REAL_HOME, ".antigravity-profile-app-*")))
                dup_dt = os.path.join(local_apps, "antigravity.desktop" if has_other_apps else "antigravity-1.desktop")
                try: os.remove(dup_dt)
                except Exception: pass
                subprocess.run(["update-desktop-database", local_apps], check=False, stderr=subprocess.DEVNULL)
                print(f"{GREEN}[SUCCESS] Regenerated desktop launcher and icons.{NC}")
            elif choice == "5":
                if is_acc1:
                    print(f"{YELLOW}[NOTICE] Account 1 profile (~/.gemini) cannot be relocated.{NC}")
                    continue
                if is_acc2:
                    print(f"{YELLOW}[NOTICE] Standard Account 2 profile (~/.antigravity-profile2) cannot be relocated.{NC}")
                    continue
                new_p = input(f"Enter new path for profile directory [current: {p_dir}]: ").strip()
                if new_p and new_p != p_dir:
                    new_p = os.path.realpath(os.path.expanduser(new_p))
                    os.makedirs(os.path.dirname(new_p), exist_ok=True)
                    shutil.move(p_dir, new_p)
                    if os.path.isfile(launcher_f):
                        update_launcher_profile_path(launcher_f, is_acc2, p_dir, new_p)
                    c['profile_dir'] = new_p
                    print(f"{GREEN}[SUCCESS] Profile directory moved to {new_p} and launcher updated.{NC}")
            elif choice == "6":
                if is_ide1:
                    print(f"\n{CYAN}--- Create Additional IDE Clone / Profile ---{NC}")
                    if os.path.isfile(manage_sh):
                        subprocess.run(["bash", manage_sh, "create-instance", "ide"], check=False)
                    break
                elif is_acc1:
                    print(f"\n{CYAN}--- Create Additional App Account Profile ---{NC}")
                    print("  [1] Standard Account 2 (antigravity-acc2)")
                    print("  [2] Custom App Profile (Named instance)")
                    sub_c = input("Choose option [1-2, Default: 1]: ").strip()
                    if sub_c == "2":
                        subprocess.run(["bash", manage_sh, "create-instance", "app"], check=False)
                    else:
                        subprocess.run(["bash", manage_sh, "app2"], check=False)
                    subprocess.run(["bash", manage_sh, "app1"], check=False)
                    break
                else:
                    c_confirm = input(f"Are you sure you want to delete clone '{c['name']}'? [y/N]: ").strip().lower()
                    if c_confirm in ["y", "yes"]:
                        if os.path.isfile(launcher_f):
                            try: os.remove(launcher_f)
                            except Exception: pass
                        if os.path.isfile(c['desktop']):
                            try: os.remove(c['desktop'])
                            except Exception: pass
                        d_prof = input(f"Also delete profile directory '{p_dir}' and its settings? [y/N]: ").strip().lower()
                        if d_prof in ["y", "yes"]:
                            shutil.rmtree(p_dir, ignore_errors=True)
                        subprocess.run(["update-desktop-database", local_apps], check=False, stderr=subprocess.DEVNULL)
                        if is_acc2 or 'app-' in cid:
                            subprocess.run(["bash", manage_sh, "app1"], check=False)
                        print(f"{GREEN}[SUCCESS] Clone '{c['name']}' removed.{NC}")
                        break
            elif choice == "7":
                old_p = eng_p
                new_p = input(f"\nEnter new installation directory path for this engine [current: {old_p}]: ").strip()
                if new_p and new_p != old_p:
                    new_p = os.path.realpath(os.path.expanduser(new_p))
                    if not os.path.isdir(new_p):
                        os.makedirs(new_p, exist_ok=True)
                    old_has = (os.path.isfile(os.path.join(old_p, 'resources', 'app.asar')) or os.path.isfile(os.path.join(old_p, 'resources', 'app', 'product.json')))
                    new_has = (os.path.isfile(os.path.join(new_p, 'resources', 'app.asar')) or os.path.isfile(os.path.join(new_p, 'resources', 'app', 'product.json')))
                    if old_has and not new_has:
                        m_ans = input(f"Copy existing installation files from {old_p} to {new_p}? [Y/n]: ").strip().lower()
                        if m_ans not in ["n", "no"]:
                            print(f"Copying files from {old_p} to {new_p}...")
                            subprocess.run(["cp", "-a", f"{old_p}/.", f"{new_p}/"], check=False)
                    if is_primary_app: curr_app = new_p
                    if is_primary_ide: curr_ide = new_p
                    if old_p in custom_paths: custom_paths.remove(old_p)
                    if new_p not in custom_paths and new_p not in [curr_app, curr_ide]: custom_paths.append(new_p)
                    u_item['engine_path'] = new_p
                    eng_p = new_p
                    if launcher_f and os.path.isfile(launcher_f):
                        old_bin = get_launcher_binary(launcher_f)
                        if old_bin.startswith(old_p):
                            new_bin = old_bin.replace(old_p, new_p, 1)
                            update_launcher_binary(launcher_f, new_bin)
                    save_paths_config(curr_app, curr_ide, custom_paths)
                    print(f"{GREEN}[SUCCESS] Engine directory relocated to: {new_p}{NC}")
            elif choice == "8":
                c_type = "ide" if "IDE" in u_item['type'] else "app"
                print(f"\n{CYAN}Downloading & installing fresh {u_item['type']} into {eng_p}...{NC}")
                flag = "--ide-dir" if c_type == "ide" else "--app-dir"
                subprocess.run(["bash", manage_sh, "install", c_type, flag, eng_p], check=False)
            elif choice == "9":
                print("\nSelect Suite Role:")
                print(f"  [1] Set as Primary App Target (Used by antigravity-1 & antigravity-acc2)")
                print(f"  [2] Set as Primary IDE Target (Used by antigravity-ide)")
                print(f"  [3] Clear Primary Target role (Keep as Secondary / Standalone)")
                r_ans = input("Choose role [1-3]: ").strip()
                if r_ans == "1":
                    curr_app = eng_p
                    print(f"{GREEN}[SUCCESS] Set {eng_p} as Primary App Target.{NC}")
                elif r_ans == "2":
                    curr_ide = eng_p
                    print(f"{GREEN}[SUCCESS] Set {eng_p} as Primary IDE Target.{NC}")
                elif r_ans == "3":
                    if is_primary_app: curr_app = ""
                    if is_primary_ide: curr_ide = ""
                    print(f"{GREEN}[SUCCESS] Cleared primary role for {eng_p}.{NC}")
            elif choice.upper() == "R":
                c_type = "ide" if "IDE" in u_item['type'] else "app"
                flag = "--ide-dir" if c_type == "ide" else "--app-dir"
                print(f"\n{CYAN}Applying RTL patch to {u_item['type']} at {eng_p}...{NC}")
                subprocess.run(["bash", manage_sh, "rtl", c_type, flag, eng_p], check=False)
            elif choice.upper() == "F" and "IDE" not in u_item.get('type', ''):
                print(f"\n{CYAN}Applying F5 reload & isolation patch to {eng_p}...{NC}")
                subprocess.run(["bash", manage_sh, "f5", "--app-dir", eng_p], check=False)
        else:
            if choice == "1":
                old_p = eng_p
                new_p = input(f"\nEnter new installation directory path [current: {old_p}]: ").strip()
                if new_p and new_p != old_p:
                    new_p = os.path.realpath(os.path.expanduser(new_p))
                    if not os.path.isdir(new_p): os.makedirs(new_p, exist_ok=True)
                    subprocess.run(["cp", "-a", f"{old_p}/.", f"{new_p}/"], check=False)
                    if is_primary_app: curr_app = new_p
                    if is_primary_ide: curr_ide = new_p
                    if old_p in custom_paths: custom_paths.remove(old_p)
                    if new_p not in custom_paths and new_p not in [curr_app, curr_ide]: custom_paths.append(new_p)
                    u_item['engine_path'] = new_p
                    eng_p = new_p
                    save_paths_config(curr_app, curr_ide, custom_paths)
                    print(f"{GREEN}[SUCCESS] Relocated to: {new_p}{NC}")
            elif choice == "2":
                print("\nSelect Suite Role:")
                print(f"  [1] Set as Primary App Target")
                print(f"  [2] Set as Primary IDE Target")
                print(f"  [3] Clear Primary Target role")
                r_ans = input("Choose role [1-3]: ").strip()
                if r_ans == "1": curr_app = eng_p; print(f"{GREEN}[SUCCESS] Set as Primary App Target.{NC}")
                elif r_ans == "2": curr_ide = eng_p; print(f"{GREEN}[SUCCESS] Set as Primary IDE Target.{NC}")
                elif r_ans == "3":
                    if is_primary_app: curr_app = ""
                    if is_primary_ide: curr_ide = ""
                    print(f"{GREEN}[SUCCESS] Cleared primary role.{NC}")
                save_paths_config(curr_app, curr_ide, custom_paths)
            elif choice == "3":
                def_name = re.sub(r'[^a-z0-9_-]+', '-', u_item['type'].lower())
                cmd_name = input(f"Enter launcher command name [default: {def_name}]: ").strip() or def_name
                exe_target = eng.get('executable') if eng else os.path.join(eng_p, 'antigravity-ide' if 'IDE' in u_item['type'] else 'antigravity')
                create_launcher_and_desktop(cmd_name, u_item['type'], exe_target, eng_p)
            elif choice == "4":
                toggle_keyring_for_path(eng_p)
            elif choice == "5":
                c_type = "ide" if "IDE" in u_item['type'] else "app"
                flag = "--ide-dir" if c_type == "ide" else "--app-dir"
                subprocess.run(["bash", manage_sh, "install", c_type, flag, eng_p], check=False)
            elif choice.upper() == "R":
                c_type = "ide" if "IDE" in u_item['type'] else "app"
                flag = "--ide-dir" if c_type == "ide" else "--app-dir"
                print(f"\n{CYAN}Applying RTL patch to {u_item['type']} at {eng_p}...{NC}")
                subprocess.run(["bash", manage_sh, "rtl", c_type, flag, eng_p], check=False)
            elif choice.upper() == "F" and "IDE" not in u_item.get('type', ''):
                print(f"\n{CYAN}Applying F5 reload & isolation patch to {eng_p}...{NC}")
                subprocess.run(["bash", manage_sh, "f5", "--app-dir", eng_p], check=False)

    return curr_app, curr_ide

def run_control_center():
    local_bin = os.path.join(REAL_HOME, ".local", "bin")
    manage_sh = os.path.join(local_bin, "manage-antigravity.sh")
    if not os.path.isfile(manage_sh):
        manage_sh = os.path.join(os.path.dirname(__file__), "manage-antigravity.sh")
    installer_sh = os.path.join(os.path.dirname(os.path.dirname(__file__)), "install.sh")

    while True:
        unified, curr_app, curr_ide, custom_paths = get_unified_instances()

        print(f"\n{CYAN}========================================================================================{NC}")
        print(f"{BOLD}{CYAN}                     Antigravity Suite Manager - Control Center                         {NC}")
        print(f"{CYAN}========================================================================================{NC}")

        print(f"{BOLD}{BLUE}[ DETECTED ANTIGRAVITY SUITE INSTANCES ({len(unified)}) ]{NC}")
        print(f"----------------------------------------------------------------------------------------")
        for idx, item in enumerate(unified, 1):
            ver_str = f"v{item['version']}" if item['version'] != "Unknown" else "Unknown"
            lnch_name = os.path.basename(item['launcher']) if item['launcher'] else "None"
            h_mode = item['history_mode']
            h_tag = f"{GREEN}{h_mode:<18}{NC}" if "Shared" in h_mode or "Master" in h_mode else (f"{YELLOW}{h_mode:<18}{NC}" if h_mode != "N/A" else f"{BLUE}{h_mode:<18}{NC}")
            k_mode = item['keyring_mode']
            k_tag = f"{GREEN}Normal{NC}" if "Normal" in k_mode else f"{BLUE}GNOME {NC}"
            name_str = item['name']
            eng_str = item['engine_path']
            print(f"  [{idx}] {name_str:<35} {ver_str:<9} in {eng_str:<18} History: {h_tag} | Keyring: {k_tag} | {lnch_name}")

        print(f"----------------------------------------------------------------------------------------")
        print(f"{BOLD}Select an installation or clone [1-{len(unified)}] to EDIT its settings.{NC}")
        print(f"Or select an action:")
        print(f"  [N] Install New Google Antigravity Binary (Download & Install)")
        print(f"  [C] Create New Clone / Account Profile (Add isolated account)")
        print(f"  [R] Apply RTL & Persian Patch to Suite (App & IDE)")
        print(f"  [E] Export Suite or History Archive (Cross-system backup/transfer)")
        print(f"  [I] Import Suite or History Archive (Restore / cross-system merge)")
        print(f"  [B] Manage History Backups (List & Restore Snapshots)")
        print(f"  [W] Run Full Setup Wizard (Sequential Steps 1-8)")
        print(f"  [S] Run a Specific Setup Step by Name (Select from named steps)")
        print(f"  [Q] Exit Setup")
        print(f"{CYAN}========================================================================================{NC}")

        try:
            choice = input(f"Select option [1-{len(unified)}, N, C, R, E, I, B, W, S, Q, Default: Q]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Control Center.")
            break

        if choice in ["0", "", "q", "Q", "exit"]:
            print("Exiting Control Center.")
            break
        elif choice.upper() == "N":
            print(f"\n{CYAN}--- Install New Google Antigravity Binary ---{NC}")
            print("Select component to install:")
            print("  [1] Antigravity App (Desktop Platform)")
            print("  [2] Antigravity IDE (VS Code Edition)")
            print("  [3] Both App & IDE")
            comp = input("Choose component [1-3, Default: 1]: ").strip()
            target_comp = "app" if comp == "1" else ("ide" if comp == "2" else "all")
            dest = input("Enter destination directory [Enter for default]: ").strip()
            cmd = ["bash", manage_sh, "install", target_comp]
            if dest:
                if target_comp == "app": cmd.extend(["--app-dir", os.path.realpath(os.path.expanduser(dest))])
                elif target_comp == "ide": cmd.extend(["--ide-dir", os.path.realpath(os.path.expanduser(dest))])
                else: cmd.extend(["--app-dir", os.path.realpath(os.path.expanduser(dest))])
            subprocess.run(cmd, check=False)
        elif choice.upper() == "C":
            print(f"\n{CYAN}--- Create New Clone / Account Profile ---{NC}")
            print("Select Profile Type to Create:")
            print("  [1] Antigravity App Profile / Clone (Account 2 or Custom App)")
            print("  [2] Antigravity IDE Profile / Clone (Secondary / Custom IDE)")
            c_type_choice = input("Enter choice [1-2, Default: 1]: ").strip()
            target_itype = "ide" if c_type_choice == "2" else "app"
            subprocess.run(["bash", manage_sh, "create-instance", target_itype], check=False)
            subprocess.run(["bash", manage_sh, "app1"], check=False)
        elif choice.upper() == "R":
            print(f"\n{CYAN}--- Apply RTL & Persian Patch to Suite ---{NC}")
            print("Select target for RTL patch:")
            print("  [1] All Targets (App + IDE + F5 reload)")
            print("  [2] Antigravity App only")
            print("  [3] Antigravity IDE only")
            r_target = input("Choose target [1-3, Default: 1]: ").strip()
            r_arg = "all" if r_target in ["1", ""] else ("app" if r_target == "2" else "ide")
            subprocess.run(["bash", manage_sh, "rtl", r_arg], check=False)
        elif choice.upper() == "E":
            print(f"\n{CYAN}--- Export Antigravity Suite or History Archive ---{NC}")
            print("Select export category:")
            print("  [1] Full Bundle (Conversation History + Brains + Suite Configs, Skills, MCP, Accounts)")
            print("  [2] History Only (Conversations, Brain artifacts, Summaries, Annotations)")
            print("  [3] Suite Configurations Only (Rules, Skills, Plugins, MCP Servers, Accounts & Tokens)")
            exp_choice = input("Enter selection [1-3, Default: 1]: ").strip()
            dest_input = input("Enter output tarball path [Enter for default ~/antigravity-...]: ").strip()

            tool_py = os.path.join(local_bin, "antigravity-migration.py")
            if not os.path.isfile(tool_py):
                tool_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antigravity-migration.py")

            cmd = [sys.executable, tool_py]
            if exp_choice == "2":
                cmd.append("export-history")
            elif exp_choice == "3":
                cmd.append("export-suite")
            else:
                cmd.append("export-all")
            if dest_input:
                cmd.append(os.path.realpath(os.path.expanduser(dest_input)))
            subprocess.run(cmd, check=False)
            input("\nPress Enter to return to Control Center...")
        elif choice.upper() == "I":
            print(f"\n{CYAN}--- Import Antigravity Suite or History Archive ---{NC}")
            arc_path = input("Enter path to archive (.tar.gz) to import: ").strip()
            if not arc_path or not os.path.isfile(os.path.realpath(os.path.expanduser(arc_path))):
                print(f"{RED}[ERROR] File not found or not specified.{NC}")
            else:
                real_arc = os.path.realpath(os.path.expanduser(arc_path))
                tool_py = os.path.join(local_bin, "antigravity-migration.py")
                if not os.path.isfile(tool_py):
                    tool_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antigravity-migration.py")
                subprocess.run([sys.executable, tool_py, "import-all", real_arc], check=False)
            input("\nPress Enter to return to Control Center...")
        elif choice.upper() == "B":
            print(f"\n{CYAN}--- Manage Antigravity History & Suite Backups ---{NC}")
            print("  [1] List Available Safety Snapshots & Backups")
            print("  [2] Create New Immediate Safety Snapshot")
            print("  [3] Restore System from a Backup Tarball")
            b_choice = input("Enter choice [1-3, Default: 1]: ").strip()
            tool_py = os.path.join(local_bin, "antigravity-migration.py")
            if not os.path.isfile(tool_py):
                tool_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "antigravity-migration.py")
            if b_choice == "2":
                subprocess.run([sys.executable, tool_py, "create-backup", "--category", "all", "--label", "manual_control_center"], check=False)
            elif b_choice == "3":
                tar_in = input("Enter path to backup archive to restore: ").strip()
                if tar_in and os.path.isfile(os.path.realpath(os.path.expanduser(tar_in))):
                    subprocess.run([sys.executable, tool_py, "restore-backup", os.path.realpath(os.path.expanduser(tar_in))], check=False)
                else:
                    print(f"{RED}[ERROR] Invalid backup path.{NC}")
            else:
                subprocess.run([sys.executable, tool_py, "list-backups"], check=False)
            input("\nPress Enter to return to Control Center...")
        elif choice.upper() == "W":
            sys.exit(10)
        elif choice.upper() == "S":
            print(f"\n{CYAN}======================================================================{NC}")
            print(f"{BOLD}{CYAN}                   Select Setup Step to Execute                       {NC}")
            print(f"{CYAN}======================================================================{NC}")
            print("  [1] Check Dependencies & Prerequisites")
            print("  [2] Configure Installation Paths & Engines")
            print("  [3] Compile Catmull-Rom Bicubic Resampler (C)")
            print("  [4] Deploy Management Tools & Master Icons")
            print("  [5] Configure Visual Icon Themes & Recolor")
            print("  [6] Configure Credential Keyring Mode (Normal vs GNOME)")
            print("  [7] Download & Install Google Antigravity Binaries")
            print("  [8] Setup Multi-Account Launchers & 3-Way Chat Sync")
            print("  [0] Return to Control Center")
            print(f"{CYAN}======================================================================{NC}")
            s_choice = input("Select step [1-8, 0 to cancel]: ").strip()
            if s_choice.isdigit() and 1 <= int(s_choice) <= 8:
                if os.path.isfile(installer_sh):
                    subprocess.run(["bash", installer_sh, "--only-step", s_choice], check=False)
                else:
                    subprocess.run(["bash", manage_sh, "wizard", "--only-step", s_choice], check=False)
        elif choice.isdigit():
            c_int = int(choice)
            if 1 <= c_int <= len(unified):
                target_item = unified[c_int - 1]
                curr_app, curr_ide = configure_unified_instance(target_item, curr_app, curr_ide, custom_paths)
                save_paths_config(curr_app, curr_ide, custom_paths)
            else:
                print(f"{RED}[ERROR] Invalid selection number '{choice}'.{NC}")
        else:
            print(f"{RED}[ERROR] Unrecognized option '{choice}'.{NC}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Antigravity System Installation Detector & Path Configurator")
    parser.add_argument('--json', action='store_true', help="Output in JSON format")
    parser.add_argument('--env', action='store_true', help="Output bash export statements")
    parser.add_argument('--configure-paths', action='store_true', help="Interactively configure and select installation paths")
    parser.add_argument('--control-center', action='store_true', help="Launch interactive Antigravity Suite Control Center")
    parser.add_argument('--clones', action='store_true', help="Output detected clones and accounts")
    parser.add_argument('--show-paths', action='store_true', help="Display currently configured installation paths")
    parser.add_argument('--set-app-dir', type=str, help="Set custom Antigravity App installation directory")
    parser.add_argument('--set-ide-dir', type=str, help="Set custom Antigravity IDE installation directory")
    parser.add_argument('--set-defaults-if-missing', action='store_true', help="Create default paths.conf if not existing")
    args = parser.parse_args()

    installs = scan_installations()

    if args.set_app_dir or args.set_ide_dir:
        curr_app, curr_ide, custom_paths = load_paths_config()
        if args.set_app_dir:
            curr_app = os.path.realpath(os.path.expanduser(args.set_app_dir))
            os.makedirs(curr_app, exist_ok=True)
        if args.set_ide_dir:
            curr_ide = os.path.realpath(os.path.expanduser(args.set_ide_dir))
            os.makedirs(curr_ide, exist_ok=True)
        save_paths_config(curr_app, curr_ide, custom_paths)
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
            app_p, ide_p, custom_paths = load_paths_config(det_app, det_ide)
            save_paths_config(app_p, ide_p, custom_paths)
    elif args.control_center:
        run_control_center()
    elif args.clones:
        clones = scan_clones()
        print(json.dumps(clones, indent=2))
    elif args.configure_paths:
        configure_paths_interactive(installs)
    elif args.show_paths:
        app_p, ide_p, custom_paths = load_paths_config()
        print(f"Antigravity App: {app_p}")
        print(f"Antigravity IDE: {ide_p}")
        if custom_paths:
            print(f"Custom Paths: {', '.join(custom_paths)}")
    elif args.json:
        print(json.dumps(installs, indent=2))
    elif args.env:
        app_path = ""
        app_ver = ""
        ide_path = ""
        ide_ver = ""
        for i in installs:
            if not app_path and ('App' in i['type'] or 'Manager' in i['type']):
                app_path = i['path']
                app_ver = i['version']
            elif not ide_path and 'IDE' in i['type']:
                ide_path = i['path']
                ide_ver = i['version']
        conf_app, conf_ide, custom_paths = load_paths_config(app_path, ide_path)
        final_app = conf_app if (conf_app and os.path.isdir(conf_app)) else (app_path or "/opt/Antigravity-x64")
        final_ide = conf_ide if (conf_ide and os.path.isdir(conf_ide)) else (ide_path or "/opt/antigravity-ide")
        print(f'ANTIGRAVITY_DETECTED_APP="{final_app}"')
        print(f'ANTIGRAVITY_DETECTED_APP_VER="{app_ver}"')
        print(f'ANTIGRAVITY_DETECTED_IDE="{final_ide}"')
        print(f'ANTIGRAVITY_DETECTED_IDE_VER="{ide_ver}"')
        if custom_paths:
            print(f'ANTIGRAVITY_CUSTOM_PATHS="{":".join(custom_paths)}"')
    else:
        print_table(installs)
