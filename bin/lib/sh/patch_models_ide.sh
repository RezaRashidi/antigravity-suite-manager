#!/usr/bin/env bash
# In-app Custom Models proxy settings patch for Antigravity IDE

patch_models_ide() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --force|-f) FORCE_INSTALL=true; shift ;;
            --ide-dir) IDE_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_rtl_dirs 2>/dev/null || auto_detect_installations 2>/dev/null || true
    if [ -z "$IDE_INSTALL_DIR" ] || [ ! -d "${IDE_INSTALL_DIR}" ]; then
        log_warn "IDE directory not found at ${IDE_INSTALL_DIR:-'<undefined>'}. Skipping IDE models patch."
        return 1
    fi
    log_info "Connecting Custom Models to Antigravity IDE at ${IDE_INSTALL_DIR}..."
    local mpy; mpy="$(get_models_py)"
    if [ -f "$mpy" ] && command -v python3 >/dev/null 2>&1; then
        python3 "$mpy" apply-ide || log_warn "Failed to apply IDE proxy settings."
    fi
    start_model_proxy_service 2>/dev/null || true
    log_success "Custom Models proxy bridge active for Antigravity IDE (jetski.cloudCodeUrl -> 50999)."
}

unpatch_models_ide() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --ide-dir) IDE_INSTALL_DIR="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_rtl_dirs 2>/dev/null || auto_detect_installations 2>/dev/null || true
    log_info "Disconnecting Custom Models from Antigravity IDE..."
    local mpy; mpy="$(get_models_py)"
    if [ -f "$mpy" ] && command -v python3 >/dev/null 2>&1; then
        python3 "$mpy" restore-ide || log_warn "Failed to restore IDE settings."
    fi
    log_success "Custom Models proxy bridge disconnected from Antigravity IDE."
}

patch_models_all() {
    log_info "Applying Custom Models patch to All Targets (App & IDE)..."
    patch_models_app "$@"
    patch_models_ide "$@"
}

unpatch_models_all() {
    log_info "Reverting Custom Models patch from All Targets (App & IDE)..."
    unpatch_models_app "$@"
    unpatch_models_ide "$@"
}
