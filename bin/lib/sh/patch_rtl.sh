#!/usr/bin/env bash
# Internal RTL application and update routines for Antigravity App and IDE

patch_rtl_app() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f) FORCE_INSTALL=true; shift ;;
            --app-dir) APP_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_rtl_dirs
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    [ ! -f "$asar" ] && { log_warn "app.asar not found at ${asar}. Skipping RTL app patch."; return 0; }

    local p_js; p_js="$(get_rtl_patch_js)" || { log_err "Internal rtl/patch_rtl.js not found."; return 1; }

    if [ "$FORCE_INSTALL" != true ] && grep -qa "ANTIGRAVITY_SUITE_RTL_PATCH_V1" "$asar"; then
        log_info "Internal RTL patch is already applied to Antigravity App. Skipping."
        return 0
    fi

    log_info "Ensuring permissions before RTL app patch..."
    fix_permissions "$APP_INSTALL_DIR"

    local orig="${asar}.orig"
    [ ! -f "$orig" ] && cp -p "$asar" "$orig"

    log_info "Applying internal RTL patch to Antigravity App (${asar})..."
    local tmp; tmp=$(mktemp -d /tmp/asar_rtl_XXXXXX)
    if ! run_asar extract "$asar" "$tmp/unpacked"; then
        log_err "Failed to extract ${asar}."
        rm -rf "$tmp"
        return 1
    fi

    if ! node "$p_js" --app "$tmp/unpacked"; then
        log_err "Internal RTL app patch failed."
        rm -rf "$tmp"
        return 1
    fi

    if ! run_asar pack "$tmp/unpacked" "$tmp/app.asar.patched" --unpack "*.node"; then
        log_err "Failed to pack patched app.asar."
        rm -rf "$tmp"
        return 1
    fi

    cp --remove-destination "$tmp/app.asar.patched" "$asar" 2>/dev/null || cp -f "$tmp/app.asar.patched" "$asar"
    rm -rf "$tmp"

    if grep -qa "ANTIGRAVITY_SUITE_RTL_PATCH_V1" "$asar"; then
        log_success "Internal RTL patch applied and verified in ${asar}."
    else
        log_err "Verification failed: RTL patch marker not found in ${asar}!"
        return 1
    fi
}

patch_rtl_ide() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f) FORCE_INSTALL=true; shift ;;
            --ide-dir) IDE_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_rtl_dirs
    check_ide_min_version "${IDE_INSTALL_DIR}" || return 1
    [ ! -d "${IDE_INSTALL_DIR}" ] && { log_warn "IDE dir not found at ${IDE_INSTALL_DIR}. Skipping RTL IDE patch."; return 0; }

    local p_js; p_js="$(get_rtl_patch_js)" || { log_err "Internal rtl/patch_rtl.js not found."; return 1; }
    local marker="${IDE_INSTALL_DIR}/resources/app/out/antigravity_rtl_patch.marker"

    if [ "$FORCE_INSTALL" != true ] && [ -f "$marker" ]; then
        log_info "Internal RTL patch is already applied to Antigravity IDE. Skipping."
        return 0
    fi

    log_info "Ensuring permissions before RTL IDE patch..."
    fix_permissions "$IDE_INSTALL_DIR"

    log_info "Applying internal RTL patch to Antigravity IDE (${IDE_INSTALL_DIR})..."
    if ! node "$p_js" --ide "${IDE_INSTALL_DIR}"; then
        log_err "Internal RTL IDE patch failed."
        return 1
    fi

    log_success "Internal RTL patch applied to Antigravity IDE."
    fix_ide_checksums "${IDE_INSTALL_DIR}"
}

patch_rtl_all() {
    patch_rtl_app "$@"
    patch_rtl_ide "$@"
}

update_rtl() {
    log_info "Applying / updating internal RTL patch..."
    ensure_rtl_dirs
    FORCE_INSTALL=true patch_rtl_all "$@"
}
