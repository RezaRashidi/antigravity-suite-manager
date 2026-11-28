#!/usr/bin/env bash
# Helper routines for Antigravity App In-App Custom Models patch

get_models_deploy_script() {
    local sdir; sdir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    local script="${sdir}/vendor/antigravity-model-proxy/scripts/deploy.mjs"
    [ -f "$script" ] && { echo "$script"; return 0; }
    local alt="${REAL_HOME:-$HOME}/.antigravity-suite-manager/vendor/antigravity-model-proxy/scripts/deploy.mjs"
    [ -f "$alt" ] && { echo "$alt"; return 0; }
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
    ACTIVE_PATCH_RTL=false; ACTIVE_PATCH_SELECTOR=false
    ACTIVE_PATCH_WINDOW_BOUNDS=false; ACTIVE_PATCH_EXPERIMENTS=false
    [ ! -f "$asar" ] && return 0

    (grep -qa "ANTIGRAVITY_SUITE_RTL" "$asar" 2>/dev/null || grep -qa "ANTIGRAVITY RTL PATCH" "$asar" 2>/dev/null) && ACTIVE_PATCH_RTL=true
    (grep -qa "ANTIGRAVITY_SUITE_SELECTOR_PATCH" "$asar" 2>/dev/null || grep -qa "multi_account_ui" "$asar" 2>/dev/null) && ACTIVE_PATCH_SELECTOR=true
    (grep -qa "ANTIGRAVITY_SUITE_EXPERIMENTS_PATCH" "$asar" 2>/dev/null || grep -qa "ANTIGRAVITY_SUITE_FORK_PATCH" "$asar" 2>/dev/null || grep -qa "FORK_EXP_PRELOAD_START" "$asar" 2>/dev/null || grep -qa "ANTIGRAVITY_SUITE_OPEN_IDE_PATCH" "$asar" 2>/dev/null) && ACTIVE_PATCH_EXPERIMENTS=true
    grep -qa "ANTIGRAVITY_SUITE_WINDOW_BOUNDS_PATCH" "$asar" 2>/dev/null && ACTIVE_PATCH_WINDOW_BOUNDS=true
    return 0
}

restore_pristine_models_base() {
    local asar="$1" orig="$2"
    detect_active_patches "$asar"
    local has_active=false
    if [ "$ACTIVE_PATCH_RTL" = "true" ] || [ "$ACTIVE_PATCH_SELECTOR" = "true" ] || \
       [ "$ACTIVE_PATCH_WINDOW_BOUNDS" = "true" ] || [ "$ACTIVE_PATCH_EXPERIMENTS" = "true" ]; then
        has_active=true
    fi
    local has_model_patch=false
    grep -qa "antigravity-model-patch" "$asar" 2>/dev/null && has_model_patch=true

    if [ "$has_model_patch" = "true" ]; then
        if [ -f "$orig" ] && ! grep -qa "antigravity-model-patch" "$orig" 2>/dev/null; then
            log_info "Temporarily restoring pristine base for model patcher..."
            cp -f "$orig" "$asar"
        fi
        return 0
    fi

    if [ ! -f "$orig" ] || [ "$has_active" != "true" ]; then
        cp -p "$asar" "$orig"
        [ "$has_active" != "true" ] && rm -rf "$(dirname "$asar")/.antigravity-model-patch" 2>/dev/null || true
        return 0
    fi
    log_info "Temporarily restoring pristine base for model patcher..."
    cp -f "$orig" "$asar"
}

reapply_post_model_patches() {
    local rtl="$1" sel="$2" arg3="${3:-false}" arg4="${4:-false}" arg5="${5:-false}" arg6="${6:-false}"
    local exp=false win_bounds=false
    if [ "$arg3" = "true" ] || [ "$arg4" = "true" ] || [ "$arg6" = "true" ]; then exp=true; fi
    if [ "$arg5" = "true" ]; then win_bounds=true; fi
    local asar="${APP_INSTALL_DIR}/resources/app.asar"
    if [ "$rtl" = "true" ]; then
        log_info "Re-applying RTL patch on top of custom models patch..."
        rm -f "${asar}.bak" 2>/dev/null || true
        FORCE_INSTALL=false patch_rtl_app >/dev/null 2>&1 || patch_rtl_app
    fi
    if [ "$sel" = "true" ]; then
        log_info "Re-applying multi-account selector on top of custom models patch..."
        FORCE_INSTALL=true patch_selector_app >/dev/null 2>&1 || patch_selector_app
    fi
    if [ "$exp" = "true" ]; then
        log_info "Re-applying Unified Experiments, Forking, Cost & Open-IDE on top of custom models patch..."
        FORCE_INSTALL=true patch_experiments_app >/dev/null 2>&1 || patch_experiments_app
    fi
    if [ "$win_bounds" = "true" ]; then
        log_info "Re-applying X11 Window Bounds patch on top of custom models patch..."
        FORCE_INSTALL=true patch_window_bounds_app >/dev/null 2>&1 || patch_window_bounds_app
    fi
}
