#!/usr/bin/env bash
# Helper routines for Antigravity App In-App Custom Models patch

get_models_deploy_script() {
    local sdir; sdir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    local script="${sdir}/vendor/antigravity-model-proxy/scripts/deploy.mjs"
    if [ -f "$script" ]; then
        echo "$script"; return 0
    fi
    local alt="${REAL_HOME:-$HOME}/.antigravity-suite-manager/vendor/antigravity-model-proxy/scripts/deploy.mjs"
    if [ -f "$alt" ]; then
        echo "$alt"; return 0
    fi
    return 1
}

ensure_models_patch_runtime() {
    if ! command -v node >/dev/null 2>&1; then
        log_err "Node.js runtime is required to apply in-app custom models patch."
        return 1
    fi
    local script; script="$(get_models_deploy_script)"
    if [ -z "$script" ] || [ ! -f "$script" ]; then
        log_err "deploy.mjs not found in vendor/antigravity-model-proxy/scripts."
        return 1
    fi
    return 0
}

detect_active_patches() {
    local asar="$1"
    ACTIVE_PATCH_F5=false
    ACTIVE_PATCH_RTL=false
    ACTIVE_PATCH_SELECTOR=false
    [ ! -f "$asar" ] && return 0

    if grep -qa "restartLanguageServer" "$asar" 2>/dev/null; then
        ACTIVE_PATCH_F5=true
    fi
    if grep -qa "ANTIGRAVITY RTL PATCH" "$asar" 2>/dev/null; then
        ACTIVE_PATCH_RTL=true
    fi
    if grep -qa "multi_account_ui" "$asar" 2>/dev/null; then
        ACTIVE_PATCH_SELECTOR=true
    fi
}

reapply_post_model_patches() {
    local f5="$1" rtl="$2" sel="$3"
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    if [ "$rtl" = "true" ]; then
        log_info "Re-applying RTL patch on top of custom models patch..."
        rm -f "${asar}.bak" 2>/dev/null || true
        FORCE_INSTALL=false patch_rtl_app >/dev/null 2>&1 || patch_rtl_app
    fi
    if [ "$f5" = "true" ]; then
        log_info "Re-applying F5 reload patch on top of custom models patch..."
        FORCE_INSTALL=true patch_f5_reload >/dev/null 2>&1 || patch_f5_reload
    fi
    if [ "$sel" = "true" ]; then
        log_info "Re-applying multi-account selector on top of custom models patch..."
        FORCE_INSTALL=true patch_selector_app >/dev/null 2>&1 || patch_selector_app
    fi
}
