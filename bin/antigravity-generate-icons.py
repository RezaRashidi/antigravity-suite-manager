#!/usr/bin/env python3
# ==============================================================================
# Antigravity High-Resolution Icon Generator & Deployer
# Supports Configurable Themes & Account 2 Recolor:
#   - Antigravity 1:   [black | white] (default: black)
#   - Antigravity 2:   [black | white] (default: black)
#   - Antigravity 2 Recolor: [true | false] (default: true -> Violet/Magenta)
#   - Antigravity IDE: [white | black] (default: white)
# Resampling: Catmull-Rom bicubic across all hicolor resolutions (16 to 512).
# ==============================================================================

import os
import sys
import struct
import zlib
import colorsys
import shutil
import subprocess
import argparse
import tempfile

REAL_USER = os.environ.get("REAL_USER")
if not REAL_USER:
    REAL_USER = os.environ.get("SUDO_USER") or os.environ.get("USER") or "root"

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

LOCAL_ICONS = os.path.join(REAL_HOME, ".local/share/icons")
LOCAL_APPS = os.path.join(REAL_HOME, ".local/share/applications")
CONFIG_FILE = os.path.join(REAL_HOME, ".config/antigravity/icons.conf")
SCALE_BIN = os.path.join(REAL_HOME, ".local/bin/scale_icon")
COLOR_CHOICES = ["original", "violet", "blue", "green", "amber", "red", "monochrome"]

def reconstruct_png(png_path):
    if not os.path.exists(png_path): return None, None, None
    try:
        with open(png_path, "rb") as f:
            sig = f.read(8)
            if sig != b"\x89PNG\r\n\x1a\n":
                return None, None, None
            idat = bytearray()
            plte = bytearray()
            trns = bytearray()
            while True:
                chunk = f.read(8)
                if not chunk: break
                l, t = struct.unpack(">I4s", chunk)
                d = f.read(l)
                f.read(4)
                if t == b"IDAT": idat.extend(d)
                elif t == b"PLTE": plte.extend(d)
                elif t == b"tRNS": trns.extend(d)
                elif t == b"IEND": break

        with open(png_path, "rb") as f:
            f.seek(16)
            w, h, bit_depth, color_type = struct.unpack(">IIBB", f.read(10))

        raw = zlib.decompress(bytes(idat))

        if color_type == 6: channels = 4
        elif color_type == 2: channels = 3
        elif color_type == 4: channels = 2
        elif color_type in (0, 3): channels = 1
        else: channels = 4

        bytes_per_sample = 2 if bit_depth == 16 else 1
        bpp = channels * bytes_per_sample
        stride = 1 + w * bpp
        recon = bytearray(w * h * bpp)

        def paeth_predictor(a, b, c):
            p = a + b - c
            pa = abs(p - a)
            pb = abs(p - b)
            pc = abs(p - c)
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

        if bit_depth == 16:
            downsampled = bytearray(w * h * channels)
            for i in range(w * h * channels):
                downsampled[i] = recon[i * 2]
            recon = downsampled

        rgba = bytearray(w * h * 4)
        if color_type == 6:
            rgba = recon
        elif color_type == 2:
            for i in range(w * h):
                rgba[i * 4] = recon[i * 3]
                rgba[i * 4 + 1] = recon[i * 3 + 1]
                rgba[i * 4 + 2] = recon[i * 3 + 2]
                rgba[i * 4 + 3] = 255
        elif color_type == 4:
            for i in range(w * h):
                v = recon[i * 2]
                a = recon[i * 2 + 1]
                rgba[i * 4] = v
                rgba[i * 4 + 1] = v
                rgba[i * 4 + 2] = v
                rgba[i * 4 + 3] = a
        elif color_type == 3:
            plte_len = len(plte)
            trns_len = len(trns)
            for i in range(w * h):
                idx = recon[i]
                if idx * 3 + 2 < plte_len:
                    rgba[i * 4] = plte[idx * 3]
                    rgba[i * 4 + 1] = plte[idx * 3 + 1]
                    rgba[i * 4 + 2] = plte[idx * 3 + 2]
                else:
                    rgba[i * 4] = rgba[i * 4 + 1] = rgba[i * 4 + 2] = 0
                rgba[i * 4 + 3] = trns[idx] if idx < trns_len else 255
        elif color_type == 0:
            for i in range(w * h):
                v = recon[i]
                rgba[i * 4] = v
                rgba[i * 4 + 1] = v
                rgba[i * 4 + 2] = v
                rgba[i * 4 + 3] = 255
        return w, h, rgba
    except Exception:
        return None, None, None

def write_png(w, h, rgba_data, out_path):
    stride = 1 + w * 4
    raw = bytearray(h * stride)
    for y in range(h):
        raw[y * stride] = 0
        raw[y * stride + 1 : (y + 1) * stride] = rgba_data[y * w * 4 : (y + 1) * w * 4]
    
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', ihdr))
        f.write(chunk(b'IDAT', idat))
        f.write(chunk(b'IEND', b''))

def resample_raw(src_data, src_w, src_h, dst_w, dst_h):
    dst = bytearray(dst_w * dst_h * 4)
    x_ratio = float(src_w) / dst_w
    y_ratio = float(src_h) / dst_h
    for y in range(dst_h):
        sy = int(y * y_ratio)
        if sy >= src_h: sy = src_h - 1
        dst_row_start = y * dst_w * 4
        src_row_start = sy * src_w * 4
        for x in range(dst_w):
            sx = int(x * x_ratio)
            if sx >= src_w: sx = src_w - 1
            src_idx = src_row_start + sx * 4
            dst_idx = dst_row_start + x * 4
            dst[dst_idx:dst_idx+4] = src_data[src_idx:src_idx+4]
    return dst

def recolor_emblem(w, h, data_in, is_white_bg=False, color="original", custom_hue=None):
    if custom_hue is None and (not color or color == "original"):
        return bytearray(data_in)
    
    color_map = {
        "violet": 0.52, "magenta": 0.52, "purple": 0.52,
        "blue": 0.60, "cyan": 0.60,
        "green": 0.32, "emerald": 0.32,
        "amber": 0.12, "gold": 0.12, "orange": 0.12,
        "red": 0.90, "ruby": 0.90,
    }
    
    is_monochrome = (color in ("monochrome", "silver", "grey", "gray")) and (custom_hue is None)
    if custom_hue is not None:
        target_hue = float(custom_hue)
    else:
        target_hue = color_map.get(color, 0.52)
    
    out = bytearray(len(data_in))
    for i in range(0, len(data_in), 4):
        r, g, b, a = data_in[i], data_in[i+1], data_in[i+2], data_in[i+3]
        if a < 10:
            out[i:i+4] = (r, g, b, a)
            continue
        
        h_val, s_val, v_val = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        
        if is_monochrome:
            if s_val > 0.08 and v_val > 0.08:
                out[i] = int(v_val * 255)
                out[i+1] = int(v_val * 255)
                out[i+2] = int(v_val * 255)
                out[i+3] = a
            else:
                out[i:i+4] = (r, g, b, a)
        else:
            if s_val > 0.15 and v_val > 0.08:
                new_h = target_hue
                new_s = min(1.0, s_val * 1.15)
                new_v = min(1.0, v_val * 1.08)
                nr, ng, nb = colorsys.hsv_to_rgb(new_h, new_s, new_v)
                out[i] = int(nr * 255)
                out[i+1] = int(ng * 255)
                out[i+2] = int(nb * 255)
                out[i+3] = a
            elif not is_white_bg and (0.04 < v_val < 0.22 and s_val < 0.25):
                nr, ng, nb = colorsys.hsv_to_rgb(target_hue, 0.40, v_val * 1.25)
                out[i] = int(nr * 255)
                out[i+1] = int(ng * 255)
                out[i+2] = int(nb * 255)
                out[i+3] = a
            else:
                out[i:i+4] = (r, g, b, a)

    return out

def main():
    # Read default configurations from config file if available
    cfg = {
        "ACC1_ICON_THEME": "black",
        "ACC1_EMBLEM_COLOR": "original",
        "ACC2_ICON_THEME": "black",
        "ACC2_EMBLEM_COLOR": "violet",
        "ACC2_RECOLOR": "true",
        "IDE_ICON_THEME": "white",
        "IDE_EMBLEM_COLOR": "original",
    }

    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        cfg[k] = v
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Antigravity Icon Generator")
    parser.add_argument("--acc1", choices=["black", "white"], default=cfg.get("ACC1_ICON_THEME", "black"),
                        help="Account 1 icon background theme (black or white)")
    parser.add_argument("--acc1-color", choices=COLOR_CHOICES, default=cfg.get("ACC1_EMBLEM_COLOR", "original"),
                        help="Account 1 emblem color")
    parser.add_argument("--acc2", choices=["black", "white"], default=cfg.get("ACC2_ICON_THEME", "black"),
                        help="Account 2 icon background theme (black or white)")
    parser.add_argument("--acc2-color", choices=COLOR_CHOICES, default=cfg.get("ACC2_EMBLEM_COLOR", "violet"),
                        help="Account 2 emblem color")
    parser.add_argument("--acc2-recolor", choices=["true", "false", "1", "0"], default=cfg.get("ACC2_RECOLOR", "true"),
                        help="Account 2 legacy color transformation (true=violet, false=original)")
    parser.add_argument("--ide", choices=["black", "white"], default=cfg.get("IDE_ICON_THEME", "white"),
                        help="Antigravity IDE icon background theme (white or black)")
    parser.add_argument("--ide-color", choices=COLOR_CHOICES, default=cfg.get("IDE_EMBLEM_COLOR", "original"),
                        help="Antigravity IDE emblem color")
    parser.add_argument("--save-config", action="store_true", help="Persist chosen options into icons.conf")
    parser.add_argument("--custom-instance", help="Generate icons for a custom instance name (e.g. antigravity-app-3)")
    parser.add_argument("--custom-theme", choices=["black", "white"], default="black", help="Base theme for custom instance")
    parser.add_argument("--custom-hue", type=float, default=None, help="Hue shift (0.0 to 1.0) for custom instance recolor")

    args = parser.parse_args()

    acc1_theme = args.acc1.lower()
    acc1_color = args.acc1_color.lower()
    acc2_theme = args.acc2.lower()
    acc2_color_passed = any(arg.startswith("--acc2-color") for arg in sys.argv)
    if not acc2_color_passed and args.acc2_recolor.lower() in ["false", "0", "no"]:
        acc2_color = "original"
    else:
        acc2_color = args.acc2_color.lower() if args.acc2_color else ("violet" if args.acc2_recolor.lower() in ["true", "1", "yes"] else "original")
    acc2_recolor = "true" if acc2_color != "original" else "false"
    ide_theme = args.ide.lower()
    ide_color = args.ide_color.lower()

    if args.save_config:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            f.write("# Antigravity Suite Icon Configuration\n")
            f.write(f'ACC1_ICON_THEME="{acc1_theme}"\n')
            f.write(f'ACC1_EMBLEM_COLOR="{acc1_color}"\n')
            f.write(f'ACC2_ICON_THEME="{acc2_theme}"\n')
            f.write(f'ACC2_EMBLEM_COLOR="{acc2_color}"\n')
            f.write(f'ACC2_RECOLOR="{acc2_recolor}"\n')
            f.write(f'IDE_ICON_THEME="{ide_theme}"\n')
            f.write(f'IDE_EMBLEM_COLOR="{ide_color}"\n')
        print(f"[INFO] Configuration saved to {CONFIG_FILE}")

    # Auto-compile scale_icon if not present
    if not os.path.isfile(SCALE_BIN) or not os.access(SCALE_BIN, os.X_OK):
        src_candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "scale_icon.c"),
            os.path.join(REAL_HOME, ".antigravity-suite-manager", "src", "scale_icon.c"),
        ]
        for sc in src_candidates:
            if os.path.isfile(sc) and shutil.which("gcc"):
                os.makedirs(os.path.dirname(SCALE_BIN), exist_ok=True)
                subprocess.run(["gcc", "-O3", sc, "-lm", "-o", SCALE_BIN], check=False)
                if os.path.isfile(SCALE_BIN):
                    try: os.chmod(SCALE_BIN, 0o755)
                    except Exception: pass
                    break

    # Master source candidates
    black_candidates = [
        os.path.join(LOCAL_ICONS, "antigravity-master-black.png"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "antigravity-master-black.png"),
        os.path.join(REAL_HOME, ".antigravity-suite-manager", "assets", "antigravity-master-black.png"),
        "/opt/Antigravity-x64/resources/icon.png",
        "/opt/antigravity2/resources/icon.png",
        "/opt/antigravity/resources/icon.png",
        "/usr/share/icons/antigravity.png",
        "/opt/Antigravity-x64/resources/app/resources/linux/code.png",
        "/opt/antigravity/resources/app/resources/linux/code.png",
        "/opt/antigravity2/resources/app/resources/linux/code.png",
    ]
    MASTER_BLACK = None
    for c in black_candidates:
        if os.path.isfile(c):
            MASTER_BLACK = c
            break

    if MASTER_BLACK and MASTER_BLACK != os.path.join(LOCAL_ICONS, "antigravity-master-black.png"):
        try:
            os.makedirs(LOCAL_ICONS, exist_ok=True)
            shutil.copy2(MASTER_BLACK, os.path.join(LOCAL_ICONS, "antigravity-master-black.png"))
        except Exception:
            pass

    white_candidates = [
        os.path.join(LOCAL_ICONS, "antigravity-master-white.png"),
        os.path.join(LOCAL_ICONS, "antigravity-ide-master.png"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "antigravity-master-white.png"),
        os.path.join(REAL_HOME, ".antigravity-suite-manager", "assets", "antigravity-master-white.png"),
        "/opt/antigravity-ide/resources/app/resources/linux/code.png",
        "/opt/antigravity/resources/app/resources/linux/code.png",
        "/opt/antigravity2/resources/app/resources/linux/code.png",
    ]
    MASTER_WHITE = None
    for c in white_candidates:
        if os.path.isfile(c):
            MASTER_WHITE = c
            break

    if MASTER_WHITE and MASTER_WHITE != os.path.join(LOCAL_ICONS, "antigravity-master-white.png"):
        try:
            os.makedirs(LOCAL_ICONS, exist_ok=True)
            shutil.copy2(MASTER_WHITE, os.path.join(LOCAL_ICONS, "antigravity-master-white.png"))
        except Exception:
            pass

    if not MASTER_BLACK:
        print("[ERROR] Master black icon not found.")
        sys.exit(1)

    if not MASTER_WHITE:
        print("[WARN] Master white icon not found. Falling back to black master.")
        MASTER_WHITE = MASTER_BLACK

    # Load Master Black & White
    w_blk, h_blk, rgba_black = reconstruct_png(MASTER_BLACK)
    w_wht, h_wht, rgba_white = reconstruct_png(MASTER_WHITE)

    if rgba_black and (w_blk, h_blk) != (1024, 1024):
        rgba_black = resample_raw(rgba_black, w_blk, h_blk, 1024, 1024)
        w_blk, h_blk = 1024, 1024

    if rgba_white and (w_wht, h_wht) != (1024, 1024):
        rgba_white = resample_raw(rgba_white, w_wht, h_wht, 1024, 1024)
        w_wht, h_wht = 1024, 1024

    if not rgba_black and rgba_white:
        rgba_black = bytearray(rgba_white)
        w_blk, h_blk = w_wht, h_wht
    elif not rgba_white and rgba_black:
        rgba_white = bytearray(rgba_black)
        w_wht, h_wht = w_blk, h_blk

    sizes = [512, 256, 128, 64, 48, 32, 24, 16]

    # Handle single custom instance generation
    if args.custom_instance:
        inst_name = args.custom_instance
        inst_theme = args.custom_theme.lower()
        base_inst = rgba_white if inst_theme == "white" else rgba_black
        if args.custom_hue is not None:
            rgba_inst = recolor_emblem(1024, 1024, base_inst, is_white_bg=(inst_theme == "white"), custom_hue=args.custom_hue)
        else:
            rgba_inst = bytearray(base_inst)
        
        icon_filename = f"{inst_name}.png"
        write_png(1024, 1024, rgba_inst, os.path.join(LOCAL_ICONS, icon_filename))
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            raw_path = os.path.join(tmp_dir, f"raw_{inst_name}_1024.raw")
            with open(raw_path, "wb") as f:
                f.write(rgba_inst)
            for sz in sizes:
                theme_dir = os.path.join(LOCAL_ICONS, "hicolor", f"{sz}x{sz}", "apps")
                os.makedirs(theme_dir, exist_ok=True)
                out_raw = os.path.join(tmp_dir, f"scaled_{sz}_{icon_filename}.raw")
                s_data = None
                if os.path.isfile(SCALE_BIN) and os.access(SCALE_BIN, os.X_OK):
                    try:
                        subprocess.run([SCALE_BIN, raw_path, "1024", "1024", out_raw, str(sz), str(sz)], check=True)
                        if os.path.isfile(out_raw):
                            with open(out_raw, "rb") as rf:
                                s_data = rf.read()
                    except Exception:
                        pass
                if not s_data:
                    s_data = resample_raw(rgba_inst, 1024, 1024, sz, sz)
                write_png(sz, sz, s_data, os.path.join(theme_dir, icon_filename))
        
        subprocess.run(["gtk-update-icon-cache", "-f", "-t", os.path.join(LOCAL_ICONS, "hicolor")], check=False)
        subprocess.run(["update-desktop-database", LOCAL_APPS], check=False)
        print(f"[SUCCESS] Custom icon {icon_filename} created in all hicolor resolutions.")
        sys.exit(0)

    print(f"[INFO] Settings: App1={acc1_theme} (Emblem: {acc1_color}), App2={acc2_theme} (Emblem: {acc2_color}), IDE={ide_theme} (Emblem: {ide_color})")

    # 1. Prepare App 1
    base_acc1 = rgba_white if acc1_theme == "white" else rgba_black
    rgba_acc1 = recolor_emblem(1024, 1024, base_acc1, is_white_bg=(acc1_theme == "white"), color=acc1_color)

    # 2. Prepare App 2
    base_acc2 = rgba_white if acc2_theme == "white" else rgba_black
    rgba_acc2 = recolor_emblem(1024, 1024, base_acc2, is_white_bg=(acc2_theme == "white"), color=acc2_color)

    # 3. Prepare IDE
    base_ide = rgba_white if ide_theme == "white" else rgba_black
    rgba_ide = recolor_emblem(1024, 1024, base_ide, is_white_bg=(ide_theme == "white"), color=ide_color)

    # Write Master Icons in ~/.local/share/icons
    write_png(1024, 1024, rgba_acc1, os.path.join(LOCAL_ICONS, "antigravity.png"))
    write_png(1024, 1024, rgba_acc1, os.path.join(LOCAL_ICONS, "antigravity-1.png"))
    write_png(1024, 1024, rgba_acc2, os.path.join(LOCAL_ICONS, "antigravity-acc2.png"))
    write_png(1024, 1024, rgba_acc2, os.path.join(LOCAL_ICONS, "antigravity-acc2-tray.png"))
    write_png(1024, 1024, rgba_ide, os.path.join(LOCAL_ICONS, "antigravity-ide.png"))

    print("[SUCCESS] Master 1024x1024 icons written.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_map = {
            "antigravity.png": (os.path.join(tmp_dir, "raw_acc1_1024.raw"), rgba_acc1),
            "antigravity-1.png": (os.path.join(tmp_dir, "raw_acc1_1024.raw"), rgba_acc1),
            "antigravity-acc2.png": (os.path.join(tmp_dir, "raw_acc2_1024.raw"), rgba_acc2),
            "antigravity-acc2-tray.png": (os.path.join(tmp_dir, "raw_acc2_1024.raw"), rgba_acc2),
            "antigravity-ide.png": (os.path.join(tmp_dir, "raw_ide_1024.raw"), rgba_ide),
        }

        for name, (raw_path, data) in raw_map.items():
            if not os.path.exists(raw_path):
                with open(raw_path, "wb") as f:
                    f.write(data)

        has_scaler = os.path.isfile(SCALE_BIN) and os.access(SCALE_BIN, os.X_OK)

        for sz in sizes:
            theme_dir = os.path.join(LOCAL_ICONS, "hicolor", f"{sz}x{sz}", "apps")
            os.makedirs(theme_dir, exist_ok=True)
            
            for name, (in_raw, rgba_data) in raw_map.items():
                dst_png = os.path.join(theme_dir, name)
                s_data = None
                if has_scaler:
                    out_raw = os.path.join(tmp_dir, f"scaled_{sz}_{name}.raw")
                    try:
                        subprocess.run([SCALE_BIN, in_raw, "1024", "1024", out_raw, str(sz), str(sz)], check=True)
                        if os.path.isfile(out_raw):
                            with open(out_raw, "rb") as rf:
                                s_data = rf.read()
                    except Exception:
                        pass
                if not s_data:
                    s_data = resample_raw(rgba_data, 1024, 1024, sz, sz)
                write_png(sz, sz, s_data, dst_png)

    print("[SUCCESS] Multi-resolution hicolor themes (16 to 512) generated.")

    # Ensure index.theme exists in hicolor for GTK validation
    index_theme = os.path.join(LOCAL_ICONS, "hicolor", "index.theme")
    if not os.path.isfile(index_theme):
        for sys_idx in ["/usr/share/icons/hicolor/index.theme", "/usr/local/share/icons/hicolor/index.theme"]:
            if os.path.isfile(sys_idx):
                try: shutil.copy2(sys_idx, index_theme)
                except Exception: pass
                break

    # Also copy top-level icons into ~/.local/share/pixmaps as standard FreeDesktop fallback
    pixmaps_dir = os.path.join(REAL_HOME, ".local/share/pixmaps")
    os.makedirs(pixmaps_dir, exist_ok=True)
    for name in ["antigravity.png", "antigravity-1.png", "antigravity-ide.png", "antigravity-acc2.png"]:
        src_f = os.path.join(LOCAL_ICONS, name)
        if os.path.isfile(src_f):
            try: shutil.copy2(src_f, os.path.join(pixmaps_dir, name))
            except Exception: pass

    # Rebuild icon caches
    subprocess.run(["gtk-update-icon-cache", "-f", "-t", os.path.join(LOCAL_ICONS, "hicolor")], check=False)
    subprocess.run(["update-desktop-database", LOCAL_APPS], check=False)

    # Live apply to windows if running
    apply_script = os.path.join(REAL_HOME, ".local/bin/antigravity-apply-icon.py")
    if os.path.isfile(apply_script):
        subprocess.run(["python3", apply_script], check=False)

    print("[SUCCESS] All desktop caches and live window icons updated.")

if __name__ == "__main__":
    main()
