"""
X11 window activation and focusing via _NET_ACTIVE_WINDOW ClientMessage.
"""

from __future__ import annotations

import ctypes
import re
import subprocess


class _XClientMessageEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p), ("window", ctypes.c_ulong), ("message_type", ctypes.c_ulong),
        ("format", ctypes.c_int), ("data", ctypes.c_long * 5)
    ]


class _XEvent(ctypes.Union):
    _fields_ = [("type", ctypes.c_int), ("xclient", _XClientMessageEvent), ("pad", ctypes.c_long * 24)]


def focus_window(target_account: str = "2") -> bool:
    """Sends _NET_ACTIVE_WINDOW event to bring target window to front."""
    d, x11 = None, None
    try:
        x11 = ctypes.CDLL('libX11.so.6')
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XDefaultRootWindow.restype = ctypes.c_ulong
        x11.XInternAtom.restype = ctypes.c_ulong

        d = x11.XOpenDisplay(None)
        if not d: return False
        root = x11.XDefaultRootWindow(d)
        atom_active = x11.XInternAtom(d, b"_NET_ACTIVE_WINDOW", False)

        res = subprocess.run(["xprop", "-root", "_NET_CLIENT_LIST"], capture_output=True, text=True)
        target_wid = None
        for wid in re.findall(r"0x[0-9a-fA-F]+", res.stdout):
            out_low = subprocess.run(["xprop", "-id", wid, "WM_CLASS"], capture_output=True, text=True).stdout.lower()
            if target_account == "2" and any(k in out_low for k in ["antigravity-2", "account2", "antigravity-acc2"]):
                target_wid = int(wid, 16); break
            elif target_account == "1" and any(k in out_low for k in ['"antigravity-1"', '"antigravity"']):
                target_wid = int(wid, 16); break
            elif target_account == "ide" and '"antigravity-ide"' in out_low:
                target_wid = int(wid, 16); break
            elif any(f'"{p}{target_account}"' in out_low for p in ["antigravity-", "antigravity-app-", "antigravity-ide-", ""]):
                target_wid = int(wid, 16); break

        if not target_wid: return False

        ev = _XEvent()
        ev.type = ev.xclient.type = 33
        ev.xclient.window = target_wid
        ev.xclient.message_type = atom_active
        ev.xclient.format = 32
        ev.xclient.data[0] = 2

        x11.XSendEvent(d, root, False, ctypes.c_long((1 << 20) | (1 << 19)), ctypes.byref(ev))
        x11.XFlush(d)
        return True
    except Exception:
        return False
    finally:
        if d and x11:
            try: x11.XCloseDisplay(d)
            except Exception: pass
