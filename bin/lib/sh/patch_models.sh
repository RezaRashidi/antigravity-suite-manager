#!/usr/bin/env bash
# In-app Custom Models Settings UI patch for Antigravity App

patch_models_app() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f) FORCE_INSTALL=true; shift ;;
            --app-dir) APP_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_rtl_dirs 2>/dev/null || auto_detect_installations 2>/dev/null || true
    ensure_models_patch_runtime || return 1
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}. Skipping in-app models patch."
        return 1
    fi
    if [ "$FORCE_INSTALL" != "true" ] && grep -qa "antigravity-model-patch" "$asar" 2>/dev/null; then
        log_info "In-app Custom Models patch is already applied to Antigravity App."
        return 0
    fi
    log_info "Ensuring permissions for ${APP_INSTALL_DIR}..."
    fix_permissions "$APP_INSTALL_DIR"
    local orig="${asar}.orig"
    restore_pristine_models_base "$asar" "$orig"
    local had_rtl="$ACTIVE_PATCH_RTL" had_sel="$ACTIVE_PATCH_SELECTOR"
    local had_fork="$ACTIVE_PATCH_FORK" had_open_ide="$ACTIVE_PATCH_OPEN_IDE"
    local had_win_bounds="$ACTIVE_PATCH_WINDOW_BOUNDS" had_typing_perf="$ACTIVE_PATCH_TYPING_PERF"
    local script; script="$(get_models_deploy_script)"
    local sdir; sdir="$(dirname "$(dirname "$script")")"
    export NODE_PATH="${sdir}/node_modules:${REAL_HOME:-$HOME}/.local/node_modules:${NODE_PATH}"
    local res_dir="${APP_INSTALL_DIR}/resources"
    log_info "Injecting Custom Models Settings UI into Antigravity App..."
    if ! node "$script" --resources "$res_dir"; then
        log_err "Failed to apply in-app custom models patch via deploy.mjs."
        [ -f "$orig" ] && cp -f "$orig" "$asar"
        return 1
    fi
    reapply_post_model_patches "$had_rtl" "$had_sel" "$had_fork" "$had_open_ide" "$had_win_bounds" "$had_typing_perf"
    if grep -qa "antigravity-model-patch" "$asar" 2>/dev/null; then
        log_success "Custom Models UI injected into Antigravity Settings successfully!"
    else
        log_err "Verification failed: antigravity-model-patch marker missing."
        return 1
    fi
}

unpatch_models_app() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --app-dir) APP_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_rtl_dirs 2>/dev/null || auto_detect_installations 2>/dev/null || true
    ensure_models_patch_runtime || return 1
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    if [ ! -f "$asar" ]; then
        log_warn "app.asar not found at ${asar:-'<undefined>'}."
        return 1
    fi
    if ! grep -qa "antigravity-model-patch" "$asar" 2>/dev/null; then
        log_info "In-app Custom Models patch is not applied to Antigravity App."
        return 0
    fi
    detect_active_patches "$asar"
    local had_rtl="$ACTIVE_PATCH_RTL" had_sel="$ACTIVE_PATCH_SELECTOR"
    local had_fork="$ACTIVE_PATCH_FORK" had_open_ide="$ACTIVE_PATCH_OPEN_IDE"
    local had_win_bounds="$ACTIVE_PATCH_WINDOW_BOUNDS" had_typing_perf="$ACTIVE_PATCH_TYPING_PERF"
    local script; script="$(get_models_deploy_script)"
    local sdir; sdir="$(dirname "$(dirname "$script")")"
    export NODE_PATH="${sdir}/node_modules:${REAL_HOME:-$HOME}/.local/node_modules:${NODE_PATH}"
    local res_dir="${APP_INSTALL_DIR}/resources"
    log_info "Restoring Antigravity App from in-app custom models patch..."
    if ! node "$script" --restore --resources "$res_dir"; then
        local orig="${asar}.orig"
        if [ -f "$orig" ]; then
            log_info "Restoring from ${orig}..."
            cp -f "$orig" "$asar"
        else
            log_err "Failed to restore custom models patch."
            return 1
        fi
    fi
    reapply_post_model_patches "$had_rtl" "$had_sel" "$had_fork" "$had_open_ide" "$had_win_bounds" "$had_typing_perf"
    log_success "In-app Custom Models patch reverted successfully."
}

