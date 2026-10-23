#!/usr/bin/env bash
# Routines to revert RTL patch from Antigravity App and IDE

unpatch_rtl_app() {
    local custom_app_dir=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --app-dir) custom_app_dir="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    [ -n "$custom_app_dir" ] && APP_INSTALL_DIR="$custom_app_dir"
    ensure_rtl_dirs

    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar}. Skipping RTL app revert."
        return 0
    fi

    if ! grep -qa "ANTIGRAVITY RTL PATCH" "$asar"; then
        log_info "RTL patch is not applied to Antigravity App at ${APP_INSTALL_DIR}."
        return 0
    fi

    log_info "Reverting RTL patch from Antigravity App (${asar})..."
    fix_permissions "$APP_INSTALL_DIR"

    if [ -f "${asar}.rtl-bak" ]; then
        cp -f "${asar}.rtl-bak" "$asar"
        rm -f "${asar}.rtl-bak"
    else
        echo "y" | run_antigravity_rtl --restore --app --path "$asar" 2>/dev/null || true
    fi

    if grep -qa "ANTIGRAVITY RTL PATCH" "$asar"; then
        echo "y" | run_antigravity_rtl --restore --app --path "$asar" 2>/dev/null || true
    fi

    if ! grep -qa "ANTIGRAVITY RTL PATCH" "$asar"; then
        log_success "RTL patch successfully reverted from Antigravity App."
    else
        log_err "Failed to revert RTL patch from Antigravity App."
        return 1
    fi
}

unpatch_rtl_ide() {
    local custom_ide_dir=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --ide-dir) custom_ide_dir="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    [ -n "$custom_ide_dir" ] && IDE_INSTALL_DIR="$custom_ide_dir"
    ensure_rtl_dirs

    if [ ! -d "${IDE_INSTALL_DIR}" ]; then
        log_warn "IDE directory not found at ${IDE_INSTALL_DIR}. Skipping RTL IDE revert."
        return 0
    fi

    local main_js="${IDE_INSTALL_DIR}/resources/app/out/main.js"
    log_info "Reverting RTL patch from Antigravity IDE (${IDE_INSTALL_DIR})..."
    fix_permissions "$IDE_INSTALL_DIR"

    if [ -f "${main_js}.rtl-bak" ]; then
        cp -f "${main_js}.rtl-bak" "$main_js"
        rm -f "${main_js}.rtl-bak"
    fi

    echo "y" | run_antigravity_rtl --restore --ide --path "${IDE_INSTALL_DIR}" 2>/dev/null || true
    fix_ide_checksums "${IDE_INSTALL_DIR}"

    if [ -f "$main_js" ] && grep -qa "antigravity-rtl-main.js" "$main_js"; then
        log_err "Failed to fully revert RTL patch from Antigravity IDE."
        return 1
    else
        log_success "RTL patch successfully reverted from Antigravity IDE."
    fi
}

unpatch_rtl_all() {
    log_info "Reverting RTL patch across all targets (App & IDE)..."
    unpatch_rtl_app "$@"
    unpatch_rtl_ide "$@"
}
