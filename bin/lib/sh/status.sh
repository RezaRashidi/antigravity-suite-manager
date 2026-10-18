#!/usr/bin/env bash
# Status inspection runner invoking status_checker.py

check_status() {
    auto_detect_installations
    if [ -z "$TARGET_APP_VER" ] || [ -z "$TARGET_IDE_VER" ]; then
        resolve_dynamic_urls >/dev/null 2>&1 || true
    fi

    local status_script
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    status_script="${script_dir}/status_checker.py"
    if [ ! -f "$status_script" ]; then
        status_script="${LOCAL_BIN}/lib/sh/status_checker.py"
    fi

    python3 "$status_script" "$APP_INSTALL_DIR" "$IDE_INSTALL_DIR" "$PROFILE2_DIR" "$APP_URL" "$IDE_URL" "$TARGET_APP_VER" "$TARGET_IDE_VER" "$CACHE_DIR" "$REAL_USER" "$ACC1_ICON_THEME" "$ACC2_ICON_THEME" "$ACC2_RECOLOR" "$IDE_ICON_THEME" "$REAL_HOME" "$LOCAL_BIN"
}
