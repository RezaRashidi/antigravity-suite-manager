"""
Display formatter and prompt renderer for unified instance configuration.
"""

from __future__ import annotations

from typing import Any, Dict

from antigravity_suite.detect.constants import BLUE, BOLD, CYAN, GREEN, NC, YELLOW


def render_unified_header(u_item: Dict[str, Any], c: Dict[str, Any] | None, p_dir: str, launcher_f: str, is_shared: bool, h_mode: str, is_normal_keyring: bool, k_mode: str, running: bool, eng_p: str, eng_v: str, role_label: str, linked_bin: str, eng: Dict[str, Any] | None) -> None:
    print(f"\n{CYAN}----------------------------------------------------------------------------------------{NC}")
    print(f"{BOLD}{CYAN}  Configuring: {u_item['name']} [{u_item['type']}]{NC}\n{CYAN}----------------------------------------------------------------------------------------{NC}")
    if c:
        print(f"  • Profile: {p_dir} | Launcher: {launcher_f}")
        print(f"  • History: {GREEN if is_shared else YELLOW}{h_mode}{NC} | Keyring: {GREEN if is_normal_keyring else BLUE}{k_mode}{NC}")
        print(f"  • Process: {GREEN if running else NC}{'Running' if running else 'Stopped'}{NC}")
    print(f"  • Engine:  {eng_p} (v{eng_v}) {role_label}")
    print(f"  • Binary:  {linked_bin or (eng.get('executable') if eng else 'Default')}")
    print(f"----------------------------------------------------------------------------------------")
    if c:
        print(f"{BOLD}Profile & Account Settings:{NC}")
        print("  [1] Toggle History Sharing Mode\n  [2] Toggle Credential Storage Mode\n  [3] Change Linked Binary")
        print("  [4] Re-generate Desktop Launcher & Icons\n  [5] Relocate / Rename Profile Directory\n  [6] Manage Clone Profile")
        print(f"\n{BOLD}Engine & Installation Settings:{NC}")
        print(f"  [7] Change / Relocate Engine Directory Path\n  [8] Download & Re-install Latest Binaries\n  [9] Set Engine as Suite Primary Target")
        print("  [U] Smart Update Engine & Patches\n  [R] Apply RTL Patch\n  [F] Apply F5 Backend Reload & Isolation Patch\n  [0] Done (Return)")
    else:
        print(f"{BOLD}Engine & Installation Settings:{NC}")
        print("  [1] Relocate Directory\n  [2] Set Primary Target\n  [3] Re-generate Launcher\n  [4] Toggle Keyring\n  [5] Re-install")
        print("  [U] Smart Update Engine & Patches\n  [R] Apply RTL Patch\n  [F] Apply F5 Reload Patch\n  [0] Done (Return)")
    print(f"{CYAN}----------------------------------------------------------------------------------------{NC}")
