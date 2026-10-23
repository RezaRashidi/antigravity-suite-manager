"""
Multi-instance inventory listing table generator.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys

G, Y, B, C, NC, BOLD = '\033[1;32m', '\033[1;33m', '\033[1;38;5;75m', '\033[1;36m', '\033[0m', '\033[1m'


def main() -> None:
    real_home = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~')
    p2_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(real_home, '.antigravity-profile2')

    print(f"{C}========================================================================================{NC}")
    print(f"{BOLD}{C}                        Antigravity Suite Multi-Instance Inventory                      {NC}")
    print(f"{C}========================================================================================{NC}")
    print(f"{BOLD}{B}Instance Name        Type   History Mode            WM_CLASS             Status   Launcher{NC}")
    print(f"----------------------------------------------------------------------------------------")

    instances = []
    p1_running = subprocess.run(["pgrep", "-f", f"user-data-dir={real_home}/.config/Antigravity"], capture_output=True).returncode == 0
    if not p1_running:
        try:
            for pid in subprocess.run(["pgrep", "-f", "Antigravity"], capture_output=True, text=True).stdout.strip().split():
                try:
                    with open(f"/proc/{pid}/cmdline", "r", errors="ignore") as f:
                        cmd = f.read()
                        if "user-data-dir=" in cmd and "/.config/Antigravity" in cmd and ".antigravity-profile" not in cmd:
                            p1_running = True; break
                except Exception: pass
        except Exception: pass
    instances.append(("Antigravity (Acc 1)", "App", "Primary (Shared)", "antigravity-1", f"{G}Running{NC}" if p1_running else "Stopped", "~/.local/bin/antigravity-1"))

    acc2_lnch = os.path.join(real_home, ".local", "bin", "antigravity-acc2")
    p2_running = subprocess.run(["pgrep", "-f", "antigravity-profile2.*Antigravity"], capture_output=True).returncode == 0
    if os.path.isdir(p2_dir) and (os.path.isfile(acc2_lnch) or p2_running):
        p2_shared = os.path.islink(os.path.join(p2_dir, ".gemini", "antigravity"))
        instances.append(("Antigravity (Acc 2)", "App", f"{G}Shared{NC}" if p2_shared else f"{Y}Isolated{NC}", "antigravity-2", f"{G}Running{NC}" if p2_running else "Stopped", "~/.local/bin/antigravity-acc2"))

    for p in sorted(glob.glob(os.path.join(real_home, ".antigravity-profile-app-*"))):
        if ".bak" in p or ".removed" in p: continue
        name = os.path.basename(p).replace(".antigravity-profile-app-", "")
        is_shared = os.path.islink(os.path.join(p, ".gemini", "antigravity"))
        is_run = subprocess.run(["pgrep", "-f", f"{os.path.basename(p)}.*Antigravity"], capture_output=True).returncode == 0
        instances.append((f"App ({name})", "App", f"{G}Shared{NC}" if is_shared else f"{Y}Isolated{NC}", f"antigravity-app-{name}", f"{G}Running{NC}" if is_run else "Stopped", f"~/.local/bin/antigravity-app-{name}"))

    ide_shared = os.path.islink(os.path.join(real_home, ".gemini", "antigravity-ide", "conversations"))
    ide_run = subprocess.run(["pgrep", "-f", "antigravity-ide"], capture_output=True).returncode == 0
    instances.append(("Antigravity IDE (1)", "IDE", f"{G}Shared{NC}" if ide_shared else f"{Y}Isolated{NC}", "antigravity-ide", f"{G}Running{NC}" if ide_run else "Stopped", "~/.local/bin/antigravity-ide"))

    for p in sorted(glob.glob(os.path.join(real_home, ".antigravity-ide-profile-*"))):
        if ".bak" in p or ".removed" in p: continue
        name = os.path.basename(p).replace(".antigravity-ide-profile-", "")
        is_shared = os.path.islink(os.path.join(p, ".gemini", "antigravity-ide", "conversations")) or os.path.islink(os.path.join(p, ".gemini", "antigravity-ide"))
        is_run = subprocess.run(["pgrep", "-f", f"{os.path.basename(p)}"], capture_output=True).returncode == 0
        instances.append((f"IDE ({name})", "IDE", f"{G}Shared{NC}" if is_shared else f"{Y}Isolated{NC}", f"antigravity-ide-{name}", f"{G}Running{NC}" if is_run else "Stopped", f"~/.local/bin/antigravity-ide-{name}"))

    for iname, itype, imode, iclass, istat, ilnch in instances:
        raw_mode = imode.replace(G, '').replace(Y, '').replace(NC, '')
        raw_stat = istat.replace(G, '').replace(NC, '')
        print(f"{iname:<20} {itype:<6} {imode:<{20 + len(imode) - len(raw_mode)}} {iclass:<24} {istat:<{10 + len(istat) - len(raw_stat)}} {ilnch}")
    print(f"{C}========================================================================================{NC}")


if __name__ == '__main__':
    main()
