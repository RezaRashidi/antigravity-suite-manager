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
    [ ! -f "$orig" ] && cp -p "$asar" "$orig"
    detect_active_patches "$asar"
    local had_f5="$ACTIVE_PATCH_F5" had_rtl="$ACTIVE_PATCH_RTL" had_sel="$ACTIVE_PATCH_SELECTOR"
    if [ "$had_f5" = "true" ] || [ "$had_rtl" = "true" ] || [ "$had_sel" = "true" ]; then
        log_info "Temporarily restoring pristine base for model patcher..."
        cp -f "$orig" "$asar"
    fi
    local script; script="$(get_models_deploy_script)"
    local res_dir="${APP_INSTALL_DIR}/resources"
    log_info "Injecting Custom Models Settings UI into Antigravity App..."
    if ! node "$script" --resources "$res_dir"; then
        log_err "Failed to apply in-app custom models patch via deploy.mjs."
        [ -f "$orig" ] && cp -f "$orig" "$asar"
        return 1
    fi
    reapply_post_model_patches "$had_f5" "$had_rtl" "$had_sel"
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
    local had_f5="$ACTIVE_PATCH_F5" had_rtl="$ACTIVE_PATCH_RTL" had_sel="$ACTIVE_PATCH_SELECTOR"
    local script; script="$(get_models_deploy_script)"
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
    reapply_post_model_patches "$had_f5" "$had_rtl" "$had_sel"
    log_success "In-app Custom Models patch reverted successfully."
}
