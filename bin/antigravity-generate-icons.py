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

REAL_HOME = os.environ.get("REAL_HOME", os.path.expanduser("~"))
LOCAL_ICONS = os.path.join(REAL_HOME, ".local/share/icons")
LOCAL_APPS = os.path.join(REAL_HOME, ".local/share/applications")
CONFIG_FILE = os.path.join(REAL_HOME, ".config/antigravity/icons.conf")
SCALE_BIN = os.path.join(REAL_HOME, ".local/bin/scale_icon")

# Read default configurations from config file if available
cfg = {
    "ACC1_ICON_THEME": "black",
    "ACC2_ICON_THEME": "black",
    "ACC2_RECOLOR": "true",
    "IDE_ICON_THEME": "white",
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
                    help="Account 1 icon theme (black or white)")
parser.add_argument("--acc2", choices=["black", "white"], default=cfg.get("ACC2_ICON_THEME", "black"),
                    help="Account 2 icon theme (black or white)")
parser.add_argument("--acc2-recolor", choices=["true", "false", "1", "0"], default=cfg.get("ACC2_RECOLOR", "true"),
                    help="Account 2 color transformation (true=violet, false=original)")
parser.add_argument("--ide", choices=["black", "white"], default=cfg.get("IDE_ICON_THEME", "white"),
                    help="Antigravity IDE icon theme (white or black)")
parser.add_argument("--save-config", action="store_true", help="Persist chosen options into icons.conf")
parser.add_argument("--custom-instance", help="Generate icons for a custom instance name (e.g. antigravity-app-3)")
parser.add_argument("--custom-theme", choices=["black", "white"], default="black", help="Base theme for custom instance")
parser.add_argument("--custom-hue", type=float, default=None, help="Hue shift (0.0 to 1.0) for custom instance recolor")

args = parser.parse_args()

acc1_theme = args.acc1.lower()
acc2_theme = args.acc2.lower()
acc2_recolor = args.acc2_recolor.lower() in ["true", "1", "yes"]
ide_theme = args.ide.lower()

if args.save_config:
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        f.write("# Antigravity Suite Icon Configuration\n")
        f.write(f'ACC1_ICON_THEME="{acc1_theme}"\n')
        f.write(f'ACC2_ICON_THEME="{acc2_theme}"\n')
        f.write(f'ACC2_RECOLOR="{"true" if acc2_recolor else "false"}"\n')
        f.write(f'IDE_ICON_THEME="{ide_theme}"\n')
    print(f"[INFO] Configuration saved to {CONFIG_FILE}")

# Master source candidates
MASTER_BLACK = os.path.join(LOCAL_ICONS, "antigravity-master-black.png")
if not os.path.isfile(MASTER_BLACK):
    for c in ["/usr/share/icons/antigravity.png", "/opt/antigravity/resources/app/resources/linux/code.png"]:
        if os.path.isfile(c):
            MASTER_BLACK = c
            break

MASTER_WHITE = os.path.join(LOCAL_ICONS, "antigravity-master-white.png")
if not os.path.isfile(MASTER_WHITE):
    MASTER_WHITE = os.path.join(LOCAL_ICONS, "antigravity-ide-master.png")

if not os.path.isfile(MASTER_BLACK):
    print("[ERROR] Master black icon not found.")
    sys.exit(1)

if not os.path.isfile(MASTER_WHITE):
    print("[WARN] Master white icon not found. Falling back to black master.")
    MASTER_WHITE = MASTER_BLACK

def reconstruct_png(png_path):
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
    return w, h, recon

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

def recolor_emblem_to_hue(w, h, data_in, is_white_bg=False, hue_shift=0.52):
    out = bytearray(len(data_in))
    for i in range(0, len(data_in), 4):
        r, g, b, a = data_in[i], data_in[i+1], data_in[i+2], data_in[i+3]
        if a < 10:
            out[i:i+4] = (r, g, b, a)
            continue
        
        h_val, s_val, v_val = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        
        # Saturated emblem gradient
        if s_val > 0.08 and v_val > 0.08:
            new_h = (h_val + hue_shift) % 1.0
            new_s = min(1.0, s_val * 1.15)
            new_v = min(1.0, v_val * 1.08)
            nr, ng, nb = colorsys.hsv_to_rgb(new_h, new_s, new_v)
            out[i] = int(nr * 255)
            out[i+1] = int(ng * 255)
            out[i+2] = int(nb * 255)
            out[i+3] = a
        elif not is_white_bg and (0.04 < v_val < 0.22 and s_val < 0.25):
            nr, ng, nb = colorsys.hsv_to_rgb((hue_shift + 0.25) % 1.0, 0.40, v_val * 1.25)
            out[i] = int(nr * 255)
            out[i+1] = int(ng * 255)
            out[i+2] = int(nb * 255)
            out[i+3] = a
        else:
            out[i:i+4] = (r, g, b, a)

    return out

def recolor_emblem_to_violet(w, h, data_in, is_white_bg=False):
    return recolor_emblem_to_hue(w, h, data_in, is_white_bg=is_white_bg, hue_shift=0.52)

# Load Master Black & White
w_blk, h_blk, rgba_black = reconstruct_png(MASTER_BLACK)
w_wht, h_wht, rgba_white = reconstruct_png(MASTER_WHITE)
sizes = [512, 256, 128, 64, 48, 32, 24, 16]

# Handle single custom instance generation
if args.custom_instance:
    inst_name = args.custom_instance
    inst_theme = args.custom_theme.lower()
    base_inst = rgba_white if inst_theme == "white" else rgba_black
    if args.custom_hue is not None:
        rgba_inst = recolor_emblem_to_hue(1024, 1024, base_inst, is_white_bg=(inst_theme == "white"), hue_shift=args.custom_hue)
    else:
        rgba_inst = bytearray(base_inst)
    
    icon_filename = f"{inst_name}.png"
    write_png(1024, 1024, rgba_inst, os.path.join(LOCAL_ICONS, icon_filename))
    
    raw_path = f"/tmp/raw_{inst_name}_1024.raw"
    with open(raw_path, "wb") as f:
        f.write(rgba_inst)
    for sz in sizes:
        theme_dir = os.path.join(LOCAL_ICONS, "hicolor", f"{sz}x{sz}", "apps")
        os.makedirs(theme_dir, exist_ok=True)
        out_raw = f"/tmp/scaled_{sz}_{icon_filename}.raw"
        subprocess.run([SCALE_BIN, raw_path, "1024", "1024", out_raw, str(sz), str(sz)], check=True)
        with open(out_raw, "rb") as rf:
            s_data = rf.read()
        write_png(sz, sz, s_data, os.path.join(theme_dir, icon_filename))
    
    subprocess.run(["gtk-update-icon-cache", "-f", "-t", os.path.join(LOCAL_ICONS, "hicolor")], check=False)
    subprocess.run(["update-desktop-database", LOCAL_APPS], check=False)
    print(f"[SUCCESS] Custom icon {icon_filename} created in all hicolor resolutions.")
    sys.exit(0)

print(f"[INFO] Settings: App1={acc1_theme}, App2={acc2_theme} (Recolor: {acc2_recolor}), IDE={ide_theme}")

# 1. Prepare App 1
rgba_acc1 = bytearray(rgba_black if acc1_theme == "black" else rgba_white)

# 2. Prepare App 2
base_acc2 = rgba_black if acc2_theme == "black" else rgba_white
if acc2_recolor:
    rgba_acc2 = recolor_emblem_to_violet(1024, 1024, base_acc2, is_white_bg=(acc2_theme == "white"))
else:
    rgba_acc2 = bytearray(base_acc2)

# 3. Prepare IDE
rgba_ide = bytearray(rgba_white if ide_theme == "white" else rgba_black)

# Write Master Icons in ~/.local/share/icons
write_png(1024, 1024, rgba_acc1, os.path.join(LOCAL_ICONS, "antigravity.png"))
write_png(1024, 1024, rgba_acc1, os.path.join(LOCAL_ICONS, "antigravity-1.png"))
write_png(1024, 1024, rgba_acc2, os.path.join(LOCAL_ICONS, "antigravity-acc2.png"))
write_png(1024, 1024, rgba_ide, os.path.join(LOCAL_ICONS, "antigravity-ide.png"))

print("[SUCCESS] Master 1024x1024 icons written.")

raw_map = {
    "antigravity.png": ("/tmp/raw_acc1_1024.raw", rgba_acc1),
    "antigravity-1.png": ("/tmp/raw_acc1_1024.raw", rgba_acc1),
    "antigravity-acc2.png": ("/tmp/raw_acc2_1024.raw", rgba_acc2),
    "antigravity-ide.png": ("/tmp/raw_ide_1024.raw", rgba_ide),
}

for name, (raw_path, data) in raw_map.items():
    with open(raw_path, "wb") as f:
        f.write(data)

for sz in sizes:
    theme_dir = os.path.join(LOCAL_ICONS, "hicolor", f"{sz}x{sz}", "apps")
    os.makedirs(theme_dir, exist_ok=True)
    
    for name, (in_raw, _) in raw_map.items():
        out_raw = f"/tmp/scaled_{sz}_{name}.raw"
        subprocess.run([SCALE_BIN, in_raw, "1024", "1024", out_raw, str(sz), str(sz)], check=True)
        with open(out_raw, "rb") as rf:
            s_data = rf.read()
        write_png(sz, sz, s_data, os.path.join(theme_dir, name))

print("[SUCCESS] Multi-resolution hicolor themes (16 to 512) generated.")

# Rebuild icon caches
subprocess.run(["gtk-update-icon-cache", "-f", "-t", os.path.join(LOCAL_ICONS, "hicolor")], check=False)
subprocess.run(["update-desktop-database", LOCAL_APPS], check=False)

# Live apply to windows if running
apply_script = os.path.join(REAL_HOME, ".local/bin/antigravity-apply-icon.py")
if os.path.isfile(apply_script):
    subprocess.run(["python3", apply_script], check=False)

print("[SUCCESS] All desktop caches and live window icons updated.")
