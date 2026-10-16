#!/usr/bin/env python3
"""
Antigravity Keyring & Credential Manager
Controls whether Antigravity App (Accounts 1 & 2) and Antigravity IDE store
credentials in GNOME Keyring (Secret Service) or in Normal / Basic local file storage.
Supports querying, live switching, token migration, and GNOME Keyring purging.
"""

import os
import sys
import json
import argparse
import subprocess
import re

GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[1;38;5;75m'
CYAN = '\033[1;36m'
RED = '\033[1;31m'
NC = '\033[0m'
BOLD = '\033[1m'

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
KEYRING_CONF = os.path.join(CONF_DIR, "keyring.conf")
LOCAL_BIN = os.path.join(REAL_HOME, ".local", "bin")

PROFILE2_DIR = os.path.join(REAL_HOME, ".antigravity-profile2")

def load_config():
    cfg = {"app1": "gnome", "app2": "normal", "ide": "gnome"}
    if os.path.isfile(KEYRING_CONF):
        try:
            with open(KEYRING_CONF, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'").lower()
                    if k == "KEYRING_MODE_APP1":
                        cfg["app1"] = v
                    elif k == "KEYRING_MODE_APP2":
                        cfg["app2"] = v
                    elif k == "KEYRING_MODE_IDE":
                        cfg["ide"] = v
        except Exception:
            pass
    return cfg

def save_config(cfg):
    os.makedirs(CONF_DIR, exist_ok=True)
    with open(KEYRING_CONF, "w", encoding="utf-8") as f:
        f.write("# Antigravity Keyring Storage Configuration\n")
        f.write("# Values: 'normal' (Basic file storage, no GNOME Keyring) or 'gnome' (GNOME Keyring)\n")
        f.write(f'KEYRING_MODE_APP1="{cfg.get("app1", "normal")}"\n')
        f.write(f'KEYRING_MODE_APP2="{cfg.get("app2", "normal")}"\n')
        f.write(f'KEYRING_MODE_IDE="{cfg.get("ide", "normal")}"\n')

def get_dbus_secrets_service():
    try:
        import dbus
        bus = dbus.SessionBus()
        secrets = bus.get_object('org.freedesktop.secrets', '/org/freedesktop/secrets')
        svc = dbus.Interface(secrets, 'org.freedesktop.Secret.Service')
        return bus, svc
    except Exception:
        return None, None

def list_keyring_items():
    bus, svc = get_dbus_secrets_service()
    if not svc:
        return []

    found = []
    try:
        import dbus
        props = dbus.Interface(bus.get_object('org.freedesktop.secrets', '/org/freedesktop/secrets'), 'org.freedesktop.DBus.Properties')
        collections = props.Get('org.freedesktop.Secret.Service', 'Collections')
        for c in collections:
            try:
                col_obj = bus.get_object('org.freedesktop.secrets', c)
                col_props = dbus.Interface(col_obj, 'org.freedesktop.DBus.Properties')
                items = col_props.Get('org.freedesktop.Secret.Collection', 'Items')
                for item in items:
                    try:
                        item_obj = bus.get_object('org.freedesktop.secrets', item)
                        item_props = dbus.Interface(item_obj, 'org.freedesktop.DBus.Properties')
                        ilabel = str(item_props.Get('org.freedesktop.Secret.Item', 'Label'))
                        attrs = {str(k): str(v) for k, v in item_props.Get('org.freedesktop.Secret.Item', 'Attributes').items()}
                        is_match = False
                        if 'antigravity' in ilabel.lower() or attrs.get('service') == 'gemini':
                            is_match = True
                        elif any('antigravity' in str(v).lower() for v in attrs.values()):
                            is_match = True
                        if is_match:
                            found.append({
                                "path": str(item),
                                "label": ilabel,
                                "attributes": attrs
                            })
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass
    return found

def get_token_from_keyring():
    bus, svc = get_dbus_secrets_service()
    if not svc:
        return None
    try:
        session = svc.OpenSession("plain", "")[1]
        search = svc.SearchItems({'service': 'gemini', 'username': 'antigravity'})
        items = list(search[0])
        if not items and search[1]:
            unlock_res = svc.Unlock(search[1])
            items.extend(unlock_res[0])
        if items:
            sec_dict = svc.GetSecrets(items, session)
            raw = bytes(sec_dict[items[0]][2]).decode('utf-8', errors='ignore')
            return raw
    except Exception:
        pass
    return None

def purge_antigravity_from_keyring():
    bus, svc = get_dbus_secrets_service()
    if not svc:
        print(f"{YELLOW}[WARN] D-Bus Secret Service not available.{NC}")
        return 0

    items = list_keyring_items()
    if not items:
        print(f"{GREEN}[INFO] No Antigravity items found in GNOME Keyring.{NC}")
        return 0

    import dbus
    deleted = 0
    for it in items:
        try:
            item_obj = bus.get_object('org.freedesktop.secrets', it['path'])
            item_iface = dbus.Interface(item_obj, 'org.freedesktop.Secret.Item')
            item_iface.Delete()
            print(f"{GREEN}[DELETED]{NC} Removed from GNOME Keyring: {it['label']} ({it['path']})")
            deleted += 1
        except Exception as e:
            print(f"{RED}[ERROR]{NC} Failed to delete {it['label']}: {e}")

    return deleted

def update_launcher_password_store(launcher_path, mode):
    if not os.path.isfile(launcher_path):
        return
    with open(launcher_path, "r", encoding="utf-8") as f:
        content = f.read()

    # If mode == normal: ensure --password-store=basic is in exec line
    # If mode == gnome: remove --password-store=basic
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if line.strip().startswith("exec "):
            if mode == "normal":
                if "--password-store=basic" not in line:
                    # insert right after exec "<path>" safely without splitting spaces in path
                    m = re.match(r'^(\s*exec\s+("[^"]+"|\'[^\']+\'|\S+))(.*)$', line)
                    if m:
                        prefix = m.group(1)
                        rest = m.group(3)
                        line = f'{prefix} --password-store=basic{rest}'
            elif mode == "gnome":
                line = line.replace("--password-store=basic ", "").replace("--password-store=basic", "")
        new_lines.append(line)

    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")
    os.chmod(launcher_path, 0o755)

def apply_mode_for_app1(mode, migrate_token=True):
    cache_file = os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable")
    token_file = os.path.join(REAL_HOME, ".gemini", "jetski-standalone-oauth-token")
    launcher = os.path.join(LOCAL_BIN, "antigravity-1")

    if mode == "normal":
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "a"):
            os.utime(cache_file, None)

        if migrate_token and not os.path.isfile(token_file):
            token_data = get_token_from_keyring()
            if token_data:
                with open(token_file, "w", encoding="utf-8") as f:
                    f.write(token_data)
                os.chmod(token_file, 0o600)
                print(f"{GREEN}[MIGRATED]{NC} Saved existing login token to {token_file}")

        update_launcher_password_store(launcher, "normal")
    else:
        if os.path.isfile(cache_file):
            try: os.remove(cache_file)
            except Exception: pass
        update_launcher_password_store(launcher, "gnome")

def apply_mode_for_app2(mode):
    cache_file = os.path.join(PROFILE2_DIR, ".gemini", "cache", "antigravity-keyring-unavailable")
    launcher = os.path.join(LOCAL_BIN, "antigravity-acc2")

    if mode == "normal":
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "a"):
            os.utime(cache_file, None)
        update_launcher_password_store(launcher, "normal")
    else:
        if os.path.isfile(cache_file):
            try: os.remove(cache_file)
            except Exception: pass
        update_launcher_password_store(launcher, "gnome")

def apply_mode_for_ide(mode):
    launcher = os.path.join(LOCAL_BIN, "antigravity-ide")
    update_launcher_password_store(launcher, mode)
    ide_cache_files = [
        os.path.join(REAL_HOME, ".gemide", "cache", "antigravity-keyring-unavailable"),
        os.path.join(REAL_HOME, ".gemini", "antigravity-ide", "cache", "antigravity-keyring-unavailable"),
    ]
    if mode == "normal":
        for cf in ide_cache_files:
            try:
                os.makedirs(os.path.dirname(cf), exist_ok=True)
                with open(cf, "a"):
                    os.utime(cf, None)
            except Exception:
                pass
    else:
        for cf in ide_cache_files:
            if os.path.isfile(cf):
                try: os.remove(cf)
                except Exception: pass

def inspect_status():
    cfg = load_config()
    print(f"{CYAN}========================================================================================{NC}")
    print(f"{BOLD}{CYAN}                    Antigravity Credential & Keyring Status                             {NC}")
    print(f"{CYAN}========================================================================================{NC}")

    # Inspect App 1
    app1_cache = os.path.isfile(os.path.join(REAL_HOME, ".gemini", "cache", "antigravity-keyring-unavailable"))
    app1_token = os.path.isfile(os.path.join(REAL_HOME, ".gemini", "jetski-standalone-oauth-token"))
    app1_l = os.path.join(LOCAL_BIN, "antigravity-1")
    app1_flag = False
    if os.path.isfile(app1_l):
        with open(app1_l, "r", errors="ignore") as f:
            app1_flag = "--password-store=basic" in f.read()

    app1_state = f"{GREEN}Normal (Plain File / No Keyring){NC}" if (app1_cache or app1_flag) else f"{YELLOW}GNOME Keyring (Secret Service){NC}"

    # Inspect App 2
    app2_cache = os.path.isfile(os.path.join(PROFILE2_DIR, ".gemini", "cache", "antigravity-keyring-unavailable"))
    app2_token = os.path.isfile(os.path.join(PROFILE2_DIR, ".gemini", "jetski-standalone-oauth-token"))
    app2_l = os.path.join(LOCAL_BIN, "antigravity-acc2")
    app2_flag = False
    if os.path.isfile(app2_l):
        with open(app2_l, "r", errors="ignore") as f:
            app2_flag = "--password-store=basic" in f.read()

    app2_state = f"{GREEN}Normal (Plain File / No Keyring){NC}" if (app2_cache or app2_flag) else f"{YELLOW}GNOME Keyring (Secret Service){NC}"

    # Inspect IDE
    ide_l = os.path.join(LOCAL_BIN, "antigravity-ide")
    ide_flag = False
    if os.path.isfile(ide_l):
        with open(ide_l, "r", errors="ignore") as f:
            ide_flag = "--password-store=basic" in f.read()
    ide_cache = any(os.path.isfile(cf) for cf in [
        os.path.join(REAL_HOME, ".gemide", "cache", "antigravity-keyring-unavailable"),
        os.path.join(REAL_HOME, ".gemini", "antigravity-ide", "cache", "antigravity-keyring-unavailable"),
    ])
    ide_state = f"{GREEN}Normal (Plain File / No Keyring){NC}" if (ide_cache or ide_flag) else f"{YELLOW}GNOME Keyring (Secret Service){NC}"

    print(f"{BOLD}{BLUE}Instance               Active Storage Mode                Local Token File    Flag (--password-store=basic){NC}")
    print(f"----------------------------------------------------------------------------------------")
    print(f"Antigravity (Acc 1)    {app1_state:<44} {'Yes (standalone)' if app1_token else 'Keyring only':<19} {'Active' if app1_flag else 'None'}")
    print(f"Antigravity (Acc 2)    {app2_state:<44} {'Yes (standalone)' if app2_token else 'Keyring only':<19} {'Active' if app2_flag else 'None'}")
    print(f"Antigravity IDE        {ide_state:<44} {'N/A (VS Code store)':<19} {'Active' if ide_flag else 'None'}")
    print(f"----------------------------------------------------------------------------------------")

    items = list_keyring_items()
    print(f"{BOLD}Items Currently Inside GNOME Keyring ({len(items)} found):{NC}")
    if items:
        for it in items:
            print(f"  • {it['label']} ({it['path']})")
            for k, v in it['attributes'].items():
                print(f"      {k}: {v}")
    else:
        print(f"  {GREEN}None (Antigravity is completely clear of GNOME Keyring){NC}")

    print(f"{CYAN}========================================================================================{NC}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antigravity Keyring Mode Switcher")
    subparsers = parser.add_subparsers(dest="action")

    subparsers.add_parser("status", help="Show keyring mode and inspect GNOME Keyring items")

    set_parser = subparsers.add_parser("set", help="Set keyring mode for instance(s)")
    set_parser.add_argument("target", choices=["app1", "app2", "ide", "all"], help="Target instance")
    set_parser.add_argument("mode", choices=["normal", "basic", "plain", "gnome", "keyring"], help="Storage mode")
    set_parser.add_argument("--purge", action="store_true", help="Purge item from GNOME Keyring after switching to normal")

    subparsers.add_parser("purge", help="Delete all Antigravity items from GNOME Keyring")

    args = parser.parse_args()

    if args.action == "status" or not args.action:
        inspect_status()
    elif args.action == "purge":
        inspect_status()
        print(f"\n{YELLOW}Purging Antigravity secrets from GNOME Keyring...{NC}")
        count = purge_antigravity_from_keyring()
        print(f"{GREEN}[SUCCESS] Purged {count} items from GNOME Keyring.{NC}")
        print("\nUpdated Status:")
        inspect_status()
    elif args.action == "set":
        cfg = load_config()
        mode_normalized = "normal" if args.mode in ["normal", "basic", "plain"] else "gnome"
        target = args.target

        if target in ["app1", "all"]:
            cfg["app1"] = mode_normalized
            apply_mode_for_app1(mode_normalized)
            print(f"{GREEN}[OK]{NC} Switched Account 1 to {mode_normalized.upper()} mode.")

        if target in ["app2", "all"]:
            cfg["app2"] = mode_normalized
            apply_mode_for_app2(mode_normalized)
            print(f"{GREEN}[OK]{NC} Switched Account 2 to {mode_normalized.upper()} mode.")

        if target in ["ide", "all"]:
            cfg["ide"] = mode_normalized
            apply_mode_for_ide(mode_normalized)
            print(f"{GREEN}[OK]{NC} Switched Antigravity IDE to {mode_normalized.upper()} mode.")

        save_config(cfg)

        if mode_normalized == "normal" and args.purge:
            print(f"\n{YELLOW}Purging Antigravity items from GNOME Keyring...{NC}")
            purge_antigravity_from_keyring()

        print("\nUpdated Status:")
        inspect_status()
