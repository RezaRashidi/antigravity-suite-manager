# Issue 13: Antigravity 1 White System Tray Icon Disparity

### Symptoms
* Antigravity 2 Desktop App system tray icon displayed with its custom colored emblem (Violet/Magenta on black).
* Antigravity 1 Desktop App system tray icon displayed as default monochrome white.

### Root Cause
* Three-fold defect across icon generation, launcher environment, and runtime synchronizer:
  1. **Launcher Environment**: `/home/reza/.local/bin/antigravity-1` exported `ANTIGRAVITY_ICON_PATH` but omitted `ANTIGRAVITY_TRAY_ICON_PATH`. Electron's `dist/tray.js` fell back to built-in monochrome white icon.
  2. **Icon Generator**: `bin/antigravity-generate-icons.py` wrote `antigravity-acc2-tray.png` but never created `antigravity-1-tray.png` or `antigravity-tray.png`.
  3. **Runtime Synchronizer**: `bin/antigravity-apply-icon.py`'s `sync_tray_cache()` only matched Account 2 processes (`antigravity-profile2`) and copied `ACC2_TRAY_PATH` over Chromium's `/tmp/org.chromium.Chromium.*/status_icon_*.png`. It completely ignored Account 1 processes.

### Solution Applied
* In [bin/antigravity-generate-icons.py](bin/antigravity-generate-icons.py): Added generation of `antigravity-1-tray.png` and `antigravity-tray.png` in 1024x1024 master, 48x48, 32x32, 24x24 in both `~/.local/share/icons/` and `hicolor/{sz}x{sz}/apps` + `hicolor/{sz}x{sz}/status`.
* In [bin/antigravity-apply-icon.py](bin/antigravity-apply-icon.py): Defined `ACC1_TRAY_PATH` and updated `sync_tray_cache()` to classify both Account 1 and Account 2 processes, copying the appropriate tray icon to `/tmp/org.chromium.Chromium.*/status_icon_*.png`.
* In [bin/manage-antigravity.sh](bin/manage-antigravity.sh) and [~/.local/bin/antigravity-1](~/.local/bin/antigravity-1): Added `export ANTIGRAVITY_TRAY_ICON_PATH="${LOCAL_ICONS}/${icon_name}-tray.png"`.
* In [bin/antigravity-f5-patch.js](bin/antigravity-f5-patch.js): Added fallback to `ANTIGRAVITY_ICON_PATH` before default white icon.

---

---
