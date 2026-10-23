#!/usr/bin/env bash
# RTL application and update routines for Antigravity App and IDE

patch_rtl_app() {
    for arg in "$@"; do [ "$arg" = "--force" ] || [ "$arg" = "-f" ] && FORCE_INSTALL=true; done
    ensure_rtl_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    [ ! -f "$asar" ] && { log_warn "app.asar not found at ${asar}. Skipping RTL app patch."; return 0; }

    if [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY RTL PATCH" "$asar"; then
        log_info "RTL patch is already applied to Antigravity App. Skipping."
        return 0
    elif [ "$FORCE_INSTALL" = true ] && grep -qa "ANTIGRAVITY RTL PATCH" "$asar"; then
        echo "y" | run_antigravity_rtl --restore --app --path "$asar" 2>/dev/null || true
    fi

    log_info "Ensuring permissions before RTL app patch..."
    fix_permissions "$APP_INSTALL_DIR"

    log_info "Applying RTL patch to Antigravity App (${asar})..."
    if ! echo "n" | run_antigravity_rtl --app --path "$asar"; then
        log_err "RTL app patch failed during execution."
        return 1
    fi

    if grep -qa "ANTIGRAVITY RTL PATCH" "$asar"; then
        log_success "RTL patch successfully applied and verified in ${asar}."
    else
        log_err "Verification failed: RTL patch marker not found in ${asar}!"
        return 1
    fi
}

patch_rtl_ide() {
    for arg in "$@"; do [ "$arg" = "--force" ] || [ "$arg" = "-f" ] && FORCE_INSTALL=true; done
    ensure_rtl_dirs
    [ ! -d "${IDE_INSTALL_DIR}" ] && { log_warn "IDE dir not found at ${IDE_INSTALL_DIR}. Skipping RTL IDE patch."; return 0; }

    local main_js="${IDE_INSTALL_DIR}/resources/app/out/main.js"
    if [ "$FORCE_INSTALL" != true ] && [ -f "$main_js" ]; then
        if grep -qa "antigravity-rtl-main.js" "$main_js" 2>/dev/null || [ -f "${main_js}.rtl-bak" ]; then
            log_info "RTL patch is already applied to Antigravity IDE. Skipping."
            return 0
        fi
    elif [ "$FORCE_INSTALL" = true ] && [ -f "${main_js}.rtl-bak" ]; then
        echo "y" | run_antigravity_rtl --restore --ide --path "${IDE_INSTALL_DIR}" 2>/dev/null || true
    fi

    log_info "Ensuring permissions before RTL IDE patch..."
    fix_permissions "$IDE_INSTALL_DIR"

    log_info "Applying RTL patch to Antigravity IDE (${IDE_INSTALL_DIR})..."
    if ! echo "n" | run_antigravity_rtl --ide --path "${IDE_INSTALL_DIR}"; then
        log_err "RTL IDE patch failed during execution."
        return 1
    fi

    log_success "RTL patch successfully applied to Antigravity IDE."
    fix_ide_checksums "${IDE_INSTALL_DIR}"
}

patch_rtl_all() {
    patch_rtl_app "$@"
    patch_rtl_ide "$@"
    patch_f5_reload "$@"
}

update_rtl() {
    log_info "Updating antigravity-rtl package..."
    npm cache clean --force 2>/dev/null || true
    ensure_rtl_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    [ -f "$asar" ] && echo "y" | run_antigravity_rtl --restore --app --path "$asar" 2>/dev/null || true
    [ -d "${IDE_INSTALL_DIR}" ] && echo "y" | run_antigravity_rtl --restore --ide --path "${IDE_INSTALL_DIR}" 2>/dev/null || true
    FORCE_INSTALL=true patch_rtl_all
    [ -d "${IDE_INSTALL_DIR}" ] && fix_ide_checksums "${IDE_INSTALL_DIR}"
}
