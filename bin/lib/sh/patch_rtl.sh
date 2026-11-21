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
    local shim_js="" rtl_v234_prepared=false
    for cand in "${SCRIPT_DIR}/bin/lib/patch/patch_rtl_v234_shim.js" "${SCRIPT_DIR}/lib/patch/patch_rtl_v234_shim.js" "${LOCAL_BIN}/lib/patch/patch_rtl_v234_shim.js"; do
        [ -f "$cand" ] && { shim_js="$cand"; break; }
    done
    if [ -n "$shim_js" ] && command -v run_asar >/dev/null 2>&1; then
        local shim_tmp; shim_tmp=$(mktemp -d /tmp/asar_rtl_shim_XXXXXX)
        if run_asar extract "$asar" "$shim_tmp/unpacked" >/dev/null 2>&1; then
            if [ "$(node "$shim_js" --prepare "$shim_tmp/unpacked" 2>/dev/null)" = "PREPARED" ]; then
                run_asar pack "$shim_tmp/unpacked" "$asar" >/dev/null 2>&1 && rtl_v234_prepared=true
            fi
        fi
        rm -rf "$shim_tmp"
    fi

    if ! echo "n" | run_antigravity_rtl --app --path "$asar"; then
        if [ "$rtl_v234_prepared" = true ] && [ -f "${asar}.bak" ]; then
            cp -f "${asar}.bak" "$asar" 2>/dev/null || true
        fi
        log_err "RTL app patch failed during execution."
        return 1
    fi

    if [ "$rtl_v234_prepared" = true ] && [ -n "$shim_js" ] && command -v run_asar >/dev/null 2>&1; then
        local shim_tmp2; shim_tmp2=$(mktemp -d /tmp/asar_rtl_shim_XXXXXX)
        if run_asar extract "$asar" "$shim_tmp2/unpacked" >/dev/null 2>&1; then
            if [ "$(node "$shim_js" --finalize "$shim_tmp2/unpacked" 2>/dev/null)" = "FINALIZED" ]; then
                run_asar pack "$shim_tmp2/unpacked" "$asar" >/dev/null 2>&1 || true
            fi
        fi
        rm -rf "$shim_tmp2"
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
    check_ide_min_version "${IDE_INSTALL_DIR}" || return 1
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
