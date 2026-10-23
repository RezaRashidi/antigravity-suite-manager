#!/usr/bin/env bash
# Detection of active patches and process management for updates

terminate_running_app() {
    local running
    running=$(pgrep -f "${APP_INSTALL_DIR}/antigravity" || true)
    if [ -n "$running" ]; then
        log_info "Stopping active Antigravity App processes before update..."
        pkill -f "${APP_INSTALL_DIR}/antigravity" 2>/dev/null || true
        pkill -f "${APP_INSTALL_DIR}/resources/bin/language_server" 2>/dev/null || true
        sleep 1.2
    fi
}

detect_active_app_patches() {
    ensure_app_install_dir
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    HAD_APP_SELECTOR=false
    HAD_APP_RTL=false
    HAD_APP_F5=false
    HAD_APP_FORK=false
    HAD_APP_OPEN_IDE=false

    [ ! -f "$asar" ] && return 0

    if grep -qa "multi_account_ui" "$asar" 2>/dev/null || grep -qa "ANTIGRAVITY_SUITE_SELECTOR_PATCH" "$asar" 2>/dev/null; then
        HAD_APP_SELECTOR=true
    fi
    if grep -qa "ANTIGRAVITY RTL PATCH" "$asar" 2>/dev/null; then
        HAD_APP_RTL=true
    fi
    if grep -qa "restartLanguageServer" "$asar" 2>/dev/null || grep -qa "ANTIGRAVITY_SUITE_F5_PATCH" "$asar" 2>/dev/null; then
        HAD_APP_F5=true
    fi
    if grep -qa "ANTIGRAVITY_SUITE_FORK_PATCH" "$asar" 2>/dev/null || grep -qa "FORK_EXP_PRELOAD_START" "$asar" 2>/dev/null; then
        HAD_APP_FORK=true
    fi
    if grep -qa "ANTIGRAVITY_SUITE_OPEN_IDE_PATCH" "$asar" 2>/dev/null; then
        HAD_APP_OPEN_IDE=true
    fi
}

detect_active_ide_patches() {
    ensure_rtl_dirs
    local wb_js="${IDE_INSTALL_DIR}/resources/app/out/vs/workbench/workbench.desktop.main.js"
    local main_js="${IDE_INSTALL_DIR}/resources/app/out/main.js"
    local fork_marker="${IDE_INSTALL_DIR}/resources/app/out/antigravity_fork_patch.marker"
    HAD_IDE_SELECTOR=false
    HAD_IDE_RTL=false
    HAD_IDE_FORK=false

    [ ! -d "$IDE_INSTALL_DIR" ] && return 0

    if [ -f "$wb_js" ] && (grep -qa "antigravity-multi-account-ide.js" "$wb_js" 2>/dev/null || grep -qa "MULTI_ACCOUNT_IDE_PATCH" "$wb_js" 2>/dev/null); then
        HAD_IDE_SELECTOR=true
    fi
    if [ -f "$main_js" ] && (grep -qa "antigravity-rtl-main.js" "$main_js" 2>/dev/null || [ -f "${main_js}.rtl-bak" ]); then
        HAD_IDE_RTL=true
    fi
    if ([ -f "$wb_js" ] && grep -qa "conversationForking:{enabled:!0" "$wb_js" 2>/dev/null) || [ -f "$fork_marker" ]; then
        HAD_IDE_FORK=true
    fi
}
