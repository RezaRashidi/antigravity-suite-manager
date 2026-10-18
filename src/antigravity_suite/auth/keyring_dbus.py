"""
D-Bus Secret Service (GNOME Keyring) integration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def get_dbus_secrets_service() -> Tuple[Any, Any]:
    """Returns DBus session bus and Secret Service interface if available."""
    try:
        import dbus
        bus = dbus.SessionBus()
        secrets = bus.get_object('org.freedesktop.secrets', '/org/freedesktop/secrets')
        return bus, dbus.Interface(secrets, 'org.freedesktop.Secret.Service')
    except Exception:
        return None, None


def list_keyring_items() -> List[Dict[str, Any]]:
    """Lists all Antigravity credential items stored in GNOME Keyring."""
    bus, svc = get_dbus_secrets_service()
    if not svc:
        return []
    found = []
    try:
        import dbus
        props = dbus.Interface(bus.get_object('org.freedesktop.secrets', '/org/freedesktop/secrets'), 'org.freedesktop.DBus.Properties')
        for c in props.Get('org.freedesktop.Secret.Service', 'Collections'):
            try:
                col_obj = bus.get_object('org.freedesktop.secrets', c)
                col_props = dbus.Interface(col_obj, 'org.freedesktop.DBus.Properties')
                for item in col_props.Get('org.freedesktop.Secret.Collection', 'Items'):
                    try:
                        item_obj = bus.get_object('org.freedesktop.secrets', item)
                        item_props = dbus.Interface(item_obj, 'org.freedesktop.DBus.Properties')
                        lbl = str(item_props.Get('org.freedesktop.Secret.Item', 'Label'))
                        attrs = {str(k): str(v) for k, v in item_props.Get('org.freedesktop.Secret.Item', 'Attributes').items()}
                        if 'antigravity' in lbl.lower() or (attrs.get('service') == 'gemini' and 'antigravity' in attrs.get('username', '').lower()) or any('antigravity' in str(v).lower() for v in attrs.values()):
                            found.append({"path": str(item), "label": lbl, "attributes": attrs})
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass
    return found


def get_token_from_keyring() -> Optional[str]:
    """Extracts the raw OAuth token stored in GNOME Keyring."""
    bus, svc = get_dbus_secrets_service()
    if not svc:
        return None
    try:
        import dbus
        session = svc.OpenSession("plain", "")[1]
        search = svc.SearchItems({'service': 'gemini', 'username': 'antigravity'})
        items = list(search[0])
        if not items and search[1]:
            unlock_res = svc.Unlock(search[1])
            items.extend(unlock_res[0])
            if not items and len(unlock_res) > 1 and str(unlock_res[1]) != "/":
                try:
                    p_obj = bus.get_object('org.freedesktop.secrets', unlock_res[1])
                    dbus.Interface(p_obj, 'org.freedesktop.Secret.Prompt').Prompt("")
                    items = list(svc.SearchItems({'service': 'gemini', 'username': 'antigravity'})[0])
                except Exception:
                    pass
        if items:
            sec_dict = svc.GetSecrets(items, session)
            return bytes(sec_dict[items[0]][2]).decode('utf-8', errors='ignore')
    except Exception:
        pass
    return None
