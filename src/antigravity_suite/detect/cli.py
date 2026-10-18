"""
CLI argument parser and entry point dispatcher for antigravity-detect.
"""

from __future__ import annotations

import argparse
import json
import os

from antigravity_suite.detect.clones_scan import scan_clones
from antigravity_suite.detect.configure_paths import configure_paths_interactive
from antigravity_suite.detect.constants import GREEN, NC, PATHS_CONF
from antigravity_suite.detect.control_center import run_control_center
from antigravity_suite.detect.paths_config import load_paths_config, save_paths_config
from antigravity_suite.detect.scan import print_table, scan_installations


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity System Installation Detector & Path Configurator")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--env", action="store_true", help="Output bash export statements")
    parser.add_argument("--configure-paths", action="store_true", help="Interactively configure and select installation paths")
    parser.add_argument("--control-center", action="store_true", help="Launch interactive Antigravity Suite Control Center")
    parser.add_argument("--clones", action="store_true", help="Output detected clones and accounts")
    parser.add_argument("--show-paths", action="store_true", help="Display currently configured installation paths")
    parser.add_argument("--set-app-dir", type=str, help="Set custom Antigravity App installation directory")
    parser.add_argument("--set-ide-dir", type=str, help="Set custom Antigravity IDE installation directory")
    parser.add_argument("--set-defaults-if-missing", action="store_true", help="Create default paths.conf if not existing")
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
        print(f"{GREEN}[SUCCESS] Saved installation paths to {PATHS_CONF}:{NC}\n  • App: {curr_app}\n  • IDE: {curr_ide}")
    elif args.set_defaults_if_missing:
        if not os.path.isfile(PATHS_CONF):
            d_app = next((i["path"] for i in installs if "App" in i["type"] or "Manager" in i["type"]), "")
            d_ide = next((i["path"] for i in installs if "IDE" in i["type"]), "")
            app_p, ide_p, custom_paths = load_paths_config(d_app, d_ide)
            save_paths_config(app_p, ide_p, custom_paths)
    elif args.control_center:
        run_control_center()
    elif args.clones:
        print(json.dumps(scan_clones(), indent=2))
    elif args.configure_paths:
        configure_paths_interactive(installs)
    elif args.show_paths:
        app_p, ide_p, custom_paths = load_paths_config()
        print(f"Antigravity App: {app_p}\nAntigravity IDE: {ide_p}")
        if custom_paths: print(f"Custom Paths: {', '.join(custom_paths)}")
    elif args.json:
        print(json.dumps(installs, indent=2))
    elif args.env:
        app_p = next((i["path"] for i in installs if "App" in i["type"] or "Manager" in i["type"]), "")
        app_v = next((i["version"] for i in installs if "App" in i["type"] or "Manager" in i["type"]), "")
        ide_p = next((i["path"] for i in installs if "IDE" in i["type"]), "")
        ide_v = next((i["version"] for i in installs if "IDE" in i["type"]), "")
        conf_app, conf_ide, custom_paths = load_paths_config(app_p, ide_p)
        final_app = conf_app if (conf_app and os.path.isdir(conf_app)) else (app_p or "/opt/Antigravity-x64")
        final_ide = conf_ide if (conf_ide and os.path.isdir(conf_ide)) else (ide_p or "/opt/antigravity-ide")
        print(f'ANTIGRAVITY_DETECTED_APP="{final_app}"\nANTIGRAVITY_DETECTED_APP_VER="{app_v}"')
        print(f'ANTIGRAVITY_DETECTED_IDE="{final_ide}"\nANTIGRAVITY_DETECTED_IDE_VER="{ide_v}"')
        if custom_paths: print(f'ANTIGRAVITY_CUSTOM_PATHS="{":".join(custom_paths)}"')
    else:
        print_table(installs)
