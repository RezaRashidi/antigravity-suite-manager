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

REAL_HOME = os.path.expanduser("~")
CONF_DIR = os.path.join(REAL_HOME, ".config", "antigravity")
PATHS_CONF = os.path.join(CONF_DIR, "paths.conf")

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
    return app_dir, ide_dir, custom_paths

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

    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write(f'exec "{exe_target}" --password-store=basic --class="{cmd_name}" --name="{cmd_name}" "$@"\n')
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
        print("  [0] Done with this installation (Return to list)")
        print(f"{CYAN}----------------------------------------------------------------------------------------{NC}")
        try:
            sub_c = input(f"Select option [0-4, Default: 0]: ").strip()
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
                        subprocess.run(f"cp -a '{old_p}/.' '{new_p}/'", shell=True, check=False)
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
        conf_app, conf_ide, custom_paths = load_paths_config()
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
        if custom_paths:
            print(f'ANTIGRAVITY_CUSTOM_PATHS="{":".join(custom_paths)}"')
    else:
        print_table(installs)
