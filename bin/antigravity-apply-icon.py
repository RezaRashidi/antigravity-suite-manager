#!/usr/bin/env python3
# ==============================================================================
# Antigravity Runtime Window & Tray Synchronizer (Account 1, Account 2, IDE)
# Enforces unique WM_CLASS and distinct icons to prevent taskbar grouping:
#   - Antigravity 1   -> WM_CLASS="antigravity-1"   (Official Black Icon)
#   - Antigravity 2   -> WM_CLASS="antigravity-2"   (Recolored Violet/Magenta Icon)
#   - Antigravity IDE -> WM_CLASS="antigravity-ide" (Official Black Icon)
# ==============================================================================
import ctypes
import os
import re
import struct
import subprocess
import sys
import time
import zlib
import glob
import shutil

REAL_HOME = os.environ.get("REAL_HOME", os.path.expanduser("~"))
ACC1_ICON_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity-1.png")
if not os.path.isfile(ACC1_ICON_PATH):
    ACC1_ICON_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity.png")

ACC2_ICON_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity-acc2.png")
IDE_ICON_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity-ide.png")
ACC2_TRAY_PATH = os.path.join(REAL_HOME, ".local/share/icons/antigravity-acc2-tray.png")

def sync_tray_cache():
    if not os.path.isfile(ACC2_TRAY_PATH):
        return
    for icon_file in glob.glob("/tmp/org.chromium.Chromium.*/status_icon_*.png"):
        try:
            shutil.copyfile(ACC2_TRAY_PATH, icon_file)
        except Exception:
            pass

def reconstruct_png(png_path):
    if not os.path.exists(png_path): return None, None, None
    try:
        with open(png_path, "rb") as f:
            f.read(8)
            idat = bytearray()
            while True:
                chunk = f.read(8)
                if not chunk: break
                l, t = struct.unpack(">I4s", chunk)
                d = f.read(l)
                f.read(4)
                if t == b"IDAT": idat.extend(d)
                elif t == b"IEND": break
        raw = zlib.decompress(bytes(idat))
        with open(png_path, "rb") as f:
            f.seek(16)
            w, h = struct.unpack(">II", f.read(8))
        bpp = 4
        stride = 1 + w * bpp
        recon = bytearray(w * h * bpp)
        def paeth_predictor(a, b, c):
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            if pa <= pb and pa <= pc: return a
            elif pb <= pc: return b
            else: return c
        for y in range(h):
            filter_type = raw[y * stride]
            scanline = raw[y * stride + 1 : (y + 1) * stride]
            recon_row = bytearray(w * bpp)
            prev_row = recon[(y - 1) * w * bpp : y * w * bpp] if y > 0 else bytearray(w * bpp)
            for x in range(w * bpp):
                filt_x = scanline[x]
                recon_a = recon_row[x - bpp] if x >= bpp else 0
                recon_b = prev_row[x]
                recon_c = prev_row[x - bpp] if x >= bpp else 0
                if filter_type == 0: val = filt_x
                elif filter_type == 1: val = (filt_x + recon_a) & 0xff
                elif filter_type == 2: val = (filt_x + recon_b) & 0xff
                elif filter_type == 3: val = (filt_x + (recon_a + recon_b) // 2) & 0xff
                elif filter_type == 4: val = (filt_x + paeth_predictor(recon_a, recon_b, recon_c)) & 0xff
                else: val = filt_x
                recon_row[x] = val
            recon[y * w * bpp : (y + 1) * w * bpp] = recon_row
        return w, h, recon
    except Exception:
        return None, None, None

def png_to_cardinal_array(png_path):
    if not os.path.exists(png_path): return None
    all_data = []
    base_name = os.path.basename(png_path)
    hicolor_dir = os.path.join(REAL_HOME, ".local/share/icons/hicolor")
    
    # Standard X11 _NET_WM_ICON sizes up to 256
    sizes = [16, 24, 32, 48, 64, 128, 256]
    for target_size in sizes:
        sz_path = os.path.join(hicolor_dir, f"{target_size}x{target_size}", "apps", base_name)
        if os.path.isfile(sz_path):
            tw, th, data = reconstruct_png(sz_path)
        else:
            w, h, orig_data = reconstruct_png(png_path)
            if not orig_data: continue
            tw = th = target_size
            data = bytearray(tw * th * 4)
            step_x, step_y = w / tw, h / th
            for ty in range(th):
                sy = int(ty * step_y)
                for tx in range(tw):
                    sx = int(tx * step_x)
                    s_idx = (sy * w + sx) * 4
                    d_idx = (ty * tw + tx) * 4
                    data[d_idx:d_idx+4] = orig_data[s_idx:s_idx+4]
        
        all_data.append(tw)
        all_data.append(th)
        for i in range(0, len(data), 4):
            r, g, b, a = data[i], data[i+1], data[i+2], data[i+3]
            argb = (a << 24) | (r << 16) | (g << 8) | b
            all_data.append(argb)
    return all_data

def focus_window(target_account="2"):
    try:
        x11 = ctypes.CDLL('libX11.so.6')
        d = x11.XOpenDisplay(None)
        if not d: return False
        root = x11.XDefaultRootWindow(d)
        atom_active = x11.XInternAtom(d, b"_NET_ACTIVE_WINDOW", False)

        res = subprocess.run(["xprop", "-root", "_NET_CLIENT_LIST"], capture_output=True, text=True)
        wids = re.findall(r"0x[0-9a-fA-F]+", res.stdout)
        target_wid = None
        for wid in wids:
            w_res = subprocess.run(["xprop", "-id", wid, "WM_CLASS"], capture_output=True, text=True)
            if target_account == "2" and ("antigravity-2" in w_res.stdout or "account2" in w_res.stdout):
                target_wid = int(wid, 16)
                break
            elif target_account == "1" and ('"antigravity-1"' in w_res.stdout or '"antigravity"' in w_res.stdout):
                target_wid = int(wid, 16)
                break
            elif target_account == "ide" and ('"antigravity-ide"' in w_res.stdout):
                target_wid = int(wid, 16)
                break
        
        if not target_wid:
            return False

        class XClientMessageEvent(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
                ("display", ctypes.c_void_p), ("window", ctypes.c_ulong), ("message_type", ctypes.c_ulong),
                ("format", ctypes.c_int), ("data", ctypes.c_long * 5)
            ]
        class XEvent(ctypes.Union):
            _fields_ = [("type", ctypes.c_int), ("xclient", XClientMessageEvent), ("pad", ctypes.c_long * 24)]

        ev = XEvent()
        ev.type = 33
        ev.xclient.type = 33
        ev.xclient.window = target_wid
        ev.xclient.message_type = atom_active
        ev.xclient.format = 32
        ev.xclient.data[0] = 2
        ev.xclient.data[1] = 0

        mask = (1 << 20) | (1 << 19)
        x11.XSendEvent(d, root, False, ctypes.c_long(mask), ctypes.byref(ev))
        x11.XFlush(d)
        return True
    except Exception:
        return False

def apply_icon_to_windows():
    sync_tray_cache()

    try:
        x11 = ctypes.CDLL('libX11.so.6')
        display = x11.XOpenDisplay(None)
        if not display: return
    except Exception:
        return

    x11.XChangeProperty.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int
    ]
    x11.XChangeProperty.restype = ctypes.c_int

    acc1_data = png_to_cardinal_array(ACC1_ICON_PATH)
    acc2_data = png_to_cardinal_array(ACC2_ICON_PATH)
    ide_data = png_to_cardinal_array(IDE_ICON_PATH)

    atom_icon = x11.XInternAtom(display, b'_NET_WM_ICON', False)
    atom_cardinal = x11.XInternAtom(display, b'CARDINAL', False)
    atom_class = x11.XInternAtom(display, b'WM_CLASS', False)
    atom_string = x11.XInternAtom(display, b'STRING', False)

    cls_acc1 = b'antigravity-1\0antigravity-1\0'
    cls_acc2 = b'antigravity-2\0antigravity-2\0'
    cls_ide = b'antigravity-ide\0antigravity-ide\0'

    c_arr_acc1 = (ctypes.c_ulong * len(acc1_data))(*acc1_data) if acc1_data else None
    c_arr_acc2 = (ctypes.c_ulong * len(acc2_data))(*acc2_data) if acc2_data else None
    c_arr_ide = (ctypes.c_ulong * len(ide_data))(*ide_data) if ide_data else None

    res = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True)
    for line in res.stdout.splitlines():
        m = re.search(r'(0x[0-9a-fA-F]+)\s+"([^"]*)":\s+\("([^"]+)"\s+"([^"]+)"\)', line)
        if not m: continue
        wid_str, title, c1, c2 = m.groups()
        if 'antigravity' in c1.lower() or 'antigravity' in c2.lower() or 'antigravity' in title.lower():
            wid = int(wid_str, 16)
            res_pid = subprocess.run(['xprop', '-id', hex(wid), '_NET_WM_PID'], capture_output=True, text=True)
            pid_match = re.search(r'=\s*(\d+)', res_pid.stdout)
            win_pid = int(pid_match.group(1)) if pid_match else None
            
            win_cmd = ""
            if win_pid:
                try:
                    with open(f"/proc/{win_pid}/cmdline", "rb") as cf:
                        win_cmd = cf.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass

            is_ide = False
            is_acc2 = False

            if "antigravity ide" in title.lower() or "antigravity-ide" in c1.lower() or (win_cmd and "/opt/antigravity/antigravity-ide" in win_cmd):
                is_ide = True
            elif "account 2" in title.lower() or "antigravity-2" in c1.lower() or "account2" in c1.lower() or (win_cmd and "antigravity-profile2" in win_cmd):
                is_acc2 = True

            if is_ide and c_arr_ide:
                x11.XChangeProperty(display, wid, atom_icon, atom_cardinal, 32, 0, ctypes.cast(c_arr_ide, ctypes.c_void_p), len(ide_data))
                x11.XChangeProperty(display, wid, atom_class, atom_string, 8, 0, cls_ide, len(cls_ide))
                x11.XFlush(display)
            elif is_acc2 and c_arr_acc2:
                x11.XChangeProperty(display, wid, atom_icon, atom_cardinal, 32, 0, ctypes.cast(c_arr_acc2, ctypes.c_void_p), len(acc2_data))
                x11.XChangeProperty(display, wid, atom_class, atom_string, 8, 0, cls_acc2, len(cls_acc2))
                x11.XFlush(display)
            elif not is_acc2 and not is_ide and c_arr_acc1:
                x11.XChangeProperty(display, wid, atom_icon, atom_cardinal, 32, 0, ctypes.cast(c_arr_acc1, ctypes.c_void_p), len(acc1_data))
                x11.XChangeProperty(display, wid, atom_class, atom_string, 8, 0, cls_acc1, len(cls_acc1))
                x11.XFlush(display)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--focus":
        acc = sys.argv[2] if len(sys.argv) > 2 else "2"
        focus_window(acc)
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        for _ in range(30):
            time.sleep(1)
            apply_icon_to_windows()
            sync_tray_cache()
    else:
        apply_icon_to_windows()
