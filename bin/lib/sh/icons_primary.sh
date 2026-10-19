#!/usr/bin/env bash
# Primary icon and tray icon synchronization and fallback assurance.

ensure_primary_icons() {
    local icon_name="$1"
    if [ ! -f "${LOCAL_ICONS}/${icon_name}.png" ]; then
        if [ -f "${LOCAL_ICONS}/antigravity-master-black.png" ]; then
            cp -f "${LOCAL_ICONS}/antigravity-master-black.png" "${LOCAL_ICONS}/${icon_name}.png" 2>/dev/null || true
        elif [ -f "${APP_INSTALL_DIR}/resources/icon.png" ]; then
            cp -f "${APP_INSTALL_DIR}/resources/icon.png" "${LOCAL_ICONS}/${icon_name}.png" 2>/dev/null || true
        fi
    fi
    if [ -f "${LOCAL_ICONS}/antigravity-1.png" ] && [ ! -f "${LOCAL_ICONS}/antigravity.png" ]; then
        cp -f "${LOCAL_ICONS}/antigravity-1.png" "${LOCAL_ICONS}/antigravity.png" 2>/dev/null || true
    elif [ -f "${LOCAL_ICONS}/antigravity.png" ] && [ ! -f "${LOCAL_ICONS}/antigravity-1.png" ]; then
        cp -f "${LOCAL_ICONS}/antigravity.png" "${LOCAL_ICONS}/antigravity-1.png" 2>/dev/null || true
    fi

    if [ ! -f "${LOCAL_ICONS}/${icon_name}-tray.png" ]; then
        if [ -f "${LOCAL_ICONS}/antigravity-1-tray.png" ]; then
            cp -f "${LOCAL_ICONS}/antigravity-1-tray.png" "${LOCAL_ICONS}/${icon_name}-tray.png" 2>/dev/null || true
        elif [ -f "${LOCAL_ICONS}/antigravity-tray.png" ]; then
            cp -f "${LOCAL_ICONS}/antigravity-tray.png" "${LOCAL_ICONS}/${icon_name}-tray.png" 2>/dev/null || true
        elif [ -f "${LOCAL_ICONS}/${icon_name}.png" ]; then
            cp -f "${LOCAL_ICONS}/${icon_name}.png" "${LOCAL_ICONS}/${icon_name}-tray.png" 2>/dev/null || true
        fi
    fi
    if [ -f "${LOCAL_ICONS}/antigravity-1-tray.png" ] && [ ! -f "${LOCAL_ICONS}/antigravity-tray.png" ]; then
        cp -f "${LOCAL_ICONS}/antigravity-1-tray.png" "${LOCAL_ICONS}/antigravity-tray.png" 2>/dev/null || true
    elif [ -f "${LOCAL_ICONS}/antigravity-tray.png" ] && [ ! -f "${LOCAL_ICONS}/antigravity-1-tray.png" ]; then
        cp -f "${LOCAL_ICONS}/antigravity-tray.png" "${LOCAL_ICONS}/antigravity-1-tray.png" 2>/dev/null || true
    fi
}

ensure_account1_icons() { ensure_primary_icons "$@"; }
