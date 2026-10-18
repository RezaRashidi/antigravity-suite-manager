"""
Terminal status table printer for Antigravity installations and patches.
"""

from __future__ import annotations

import os
import sys

# Ensure local dir is in sys.path
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

from status_env_inspect import (
    check_account2,
    check_cached,
    check_customization_sharing,
    check_history_sharing,
    check_keyring_storage,
    check_write,
    scan_all_installations,
)
from status_inspect import B, BOLD, C, G, NC, R, Y, check_app_f5, check_app_rtl, check_ide_rtl, get_app_version, get_ide_version


def main() -> None:
    app_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    ide_dir = sys.argv[2] if len(sys.argv) > 2 else ""
    prof2_dir = sys.argv[3] if len(sys.argv) > 3 else ""
    app_url = sys.argv[4] if len(sys.argv) > 4 else ""
    ide_url = sys.argv[5] if len(sys.argv) > 5 else ""
    targ_app_ver = sys.argv[6] if len(sys.argv) > 6 else ""
    targ_ide_ver = sys.argv[7] if len(sys.argv) > 7 else ""
    cache_dir = sys.argv[8] if len(sys.argv) > 8 else "/tmp/antigravity-cache"
    real_user = sys.argv[9] if len(sys.argv) > 9 else os.environ.get("USER", "user")
    acc1_theme = sys.argv[10] if len(sys.argv) > 10 else "black"
    acc2_theme = sys.argv[11] if len(sys.argv) > 11 else "black"
    acc2_recolor = sys.argv[12].lower() in ["true", "1", "yes"] if len(sys.argv) > 12 else True
    ide_theme = sys.argv[13] if len(sys.argv) > 13 else "white"
    real_home = sys.argv[14] if len(sys.argv) > 14 else os.path.expanduser("~")
    local_bin = sys.argv[15] if len(sys.argv) > 15 else os.path.join(real_home, ".local", "bin")

    app_ver, ide_ver = get_app_version(app_dir), get_ide_version(ide_dir)
    app_st = f"{G}Up-to-date{NC}" if (app_ver and app_ver == targ_app_ver) else (f"{Y}Update Available{NC}" if app_ver else f"{R}Not Installed{NC}")
    ide_st = f"{G}Up-to-date{NC}" if (ide_ver and ide_ver == targ_ide_ver) else (f"{Y}Update Available{NC}" if ide_ver else f"{R}Not Installed{NC}")
    app_rtl, app_f5, ide_rtl = check_app_rtl(app_dir), check_app_f5(app_dir), check_ide_rtl(ide_dir)

    print(f"{C}========================================================================================{NC}")
    print(f"{BOLD}{C}                    Antigravity Suite Version & Patch Inspection                        {NC}")
    print(f"{C}========================================================================================{NC}")
    print(f"{BOLD}{B}Target                 Installed    Latest Available  Status          RTL Patch   F5 Patch{NC}")
    print(f"----------------------------------------------------------------------------------------")
    print(f"Antigravity (Acc 1&2)  {app_ver or 'N/A':<12} {targ_app_ver:<17} {app_st:<24} {app_rtl:<20} {app_f5}")
    print(f"Antigravity IDE        {ide_ver or 'N/A':<12} {targ_ide_ver:<17} {ide_st:<24} {ide_rtl:<20} N/A")
    print(f"----------------------------------------------------------------------------------------")
    print(f"{BOLD}Detected System Installations:{NC}")
    installs = scan_all_installations()
    if installs:
        for itype, iver, ipath in installs:
            tag = f" {G}[Primary App]{NC}" if (app_dir and os.path.realpath(ipath) == os.path.realpath(app_dir)) else (f" {G}[Primary IDE]{NC}" if (ide_dir and os.path.realpath(ipath) == os.path.realpath(ide_dir)) else "")
            print(f"  • {itype:<20} v{iver:<10} in {ipath}{tag}")
    else:
        print(f"  {Y}None detected outside default locations.{NC}")
    print(f"----------------------------------------------------------------------------------------")
    print(f"{BOLD}Package Cache Status in {cache_dir}:{NC}")
    print(f"  • Antigravity App:        {check_cached(cache_dir, 'Antigravity-App', targ_app_ver)}")
    print(f"  • Antigravity IDE:        {check_cached(cache_dir, 'Antigravity-IDE', targ_ide_ver)}")
    print(f"----------------------------------------------------------------------------------------")
    print(f"{BOLD}Icon & Appearance Themes:{NC}")
    print(f"  • Antigravity (Acc 1):    {acc1_theme.capitalize()} Icon Theme")
    rc_badge = f"{G}Violet/Magenta Glow (Recolored){NC}" if acc2_recolor else f"{Y}Original Colors (No Recolor){NC}"
    print(f"  • Antigravity (Acc 2):    {acc2_theme.capitalize()} Icon Theme | {rc_badge}")
    print(f"  • Antigravity IDE:        {ide_theme.capitalize()} Icon Theme")
    print(f"----------------------------------------------------------------------------------------")
    print(f"{BOLD}Environment & Permissions:{NC}")
    print(f"  • Account 2 Status:       {check_account2(prof2_dir)}")
    print(f"  • Keyring Storage Mode:   {check_keyring_storage(real_home, local_bin, prof2_dir)}")
    print(f"  • History Sharing:        {check_history_sharing(prof2_dir)}")
    print(f"  • Customizations Sharing: {check_customization_sharing(prof2_dir)}")
    print(f"  • App Dir Ownership:      {check_write(app_dir, real_user)}")
    print(f"  • IDE Dir Ownership:      {check_write(ide_dir, real_user)}")
    print(f"  • Discovered App URL:     {app_url}\n  • Discovered IDE URL:     {ide_url}")
    print(f"{C}========================================================================================{NC}")


if __name__ == "__main__":
    main()
