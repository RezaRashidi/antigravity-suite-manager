"""
GNOME Keyring credential purging operations.
"""

from __future__ import annotations

from antigravity_suite.auth.keyring_constants import GREEN, NC, RED, YELLOW
from antigravity_suite.auth.keyring_dbus import get_dbus_secrets_service, list_keyring_items


def purge_antigravity_from_keyring(target: str = "all") -> int:
    """Purges Antigravity credential entries from GNOME Keyring."""
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
        lbl = it['label'].lower()
        attrs = {str(k).lower(): str(v).lower() for k, v in it.get('attributes', {}).items()}
        if target == "app1" and ("ide" in lbl or any("ide" in v for v in attrs.values()) or "acc2" in lbl or "profile2" in lbl):
            continue
        if target == "app2" and not ("acc2" in lbl or "profile2" in lbl or "antigravity-2" in lbl):
            continue
        if target == "ide" and not ("ide" in lbl or any("ide" in v for v in attrs.values())):
            continue
        try:
            item_iface = dbus.Interface(bus.get_object('org.freedesktop.secrets', it['path']), 'org.freedesktop.Secret.Item')
            del_p = item_iface.Delete()
            if del_p and str(del_p) != "/":
                try:
                    dbus.Interface(bus.get_object('org.freedesktop.secrets', del_p), 'org.freedesktop.Secret.Prompt').Prompt("")
                except Exception:
                    pass
            print(f"{GREEN}[DELETED]{NC} Removed from GNOME Keyring: {it['label']} ({it['path']})")
            deleted += 1
        except Exception as e:
            print(f"{RED}[ERROR]{NC} Failed to delete {it['label']}: {e}")
    return deleted
