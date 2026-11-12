# Forensic Analysis Case 59: App v2.30+ X11 `BaseWindow` Maximize/Resize Cutoff & Dynamic Ozone Auto-Detection

## Executive Summary

Starting in Antigravity Desktop App v2.30+ (verified on `2.31.2` / `Electron 44.9.1`), maximizing or resizing the app window under X11 (`titleBarStyle: 'hidden'`) clipped the bottom of the viewport and broke layout responsiveness during resizes. The same build rendered cleanly under native Wayland.

We resolved both layers:
1. Replaced hardcoded `ELECTRON_OZONE_PLATFORM_HINT="x11"` launcher configuration with runtime Wayland/X11/auto display-server detection so Wayland sessions run natively without Chromium fallback quirks.
2. Added a standalone `patch-window` / `unpatch-window` ASAR patcher for X11 sessions to resynchronize child `WebContentsView` bounds after Chromium/WM frame extents settle.

---

## Detailed Root Cause Analysis

1. **Hardcoded X11 Forced Fallback**: Generated launchers (`antigravity-1`, `antigravity-ide`, and custom IDE instances) hardcoded `ELECTRON_OZONE_PLATFORM_HINT="x11"`, forcing XWayland/X11 even when `WAYLAND_DISPLAY` was active.
2. **Stale `BaseWindow.getContentSize()` During X11 `resize` Events**: Live Electron inspection on `DISPLAY=:0` showed `syncHubViewBounds` executing synchronously inside the `BaseWindow` `resize` handler while `baseWin.getContentSize()` still reported lagged frame-inclusive dimensions (`[1952, 1204]` on a `1920x1162` maximized display — `+32px` width, `+42px` height).
3. Because `hubWcv` and `curtainView` were sized to `[1952, 1204]` before the X11 window manager finished committing client extents, the bottom ~42px of the chat input and footer clipped off-screen.

---

## Resolution

### 1. Dynamic Display-Server Auto-Detection
- Added shared `detect_ozone_platform()` and `emit_launcher_ozone_detect()` helpers in `bin/lib/sh/env.sh`.
- Updated `bin/manage-antigravity.sh`, `bin/lib/sh/app_launcher.sh`, `bin/lib/sh/ide_launcher.sh`, and `bin/lib/sh/instance_create_ide.sh` to detect `wayland`, `x11`, or `auto` at runtime (`OZONE_FLAG`, `--ozone-platform=...`) and apply the X11 icon guard selectively.

### 2. Standalone X11 `BaseWindow` Bounds Patch (`patch-window` / `unpatch-window`)
- Implemented AST/source patcher `bin/lib/patch/patch_window_bounds.js` (`ANTIGRAVITY_SUITE_WINDOW_BOUNDS_PATCH_V1`):
  - Schedules deferred `[16, 80, 200, 450]` ms settle resyncs after `resize` events so child views match finalized `baseWin.getContentSize()`.
  - Hooks `maximize`, `unmaximize`, `enter-full-screen`, `leave-full-screen`, and `show` events to force resync, with timer cleanup on `closed`.
- Added shell wrapper `bin/lib/sh/patch_window_bounds.sh` (`patch-window` / `unpatch-window`), CLI routing (`cli_parse.sh`, `cli_flags.sh`, `cli_dispatch.sh`, `cli_dispatch_patches.sh`, `help.sh`), `patch_all.sh`, auto-reapply across `suite_update*.sh`, `downgrade.sh`, `patch_models*.sh`, and status reporting (`check_app_window_bounds` in `status_inspect.py`).

---

## Verification

- Added unit and integration coverage in `tests/test_window_bounds_patch.py` and updated launcher validation in `tests/test_fixes_validation.py`.
- Applied `bash bin/manage-antigravity.sh patch-window --app-dir /opt/Antigravity-x64` against App `2.31.2` (`resources/app.asar`) and confirmed `status` reports `WindowBounds: Applied` alongside `OpenIDE`, `Selector`, `Fork`, and `Models`.
- Verified shell syntax (`bash -n`), JS syntax (`node --check bin/lib/patch/patch_window_bounds.js`), and targeted `unittest` suites pass.
